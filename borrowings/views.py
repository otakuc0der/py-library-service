from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from books.models import Book
from borrowings.filters import BorrowingFilter
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingDetailSerializer,
    BorrowingListSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Borrowings"],
        summary="List borrowings",
        description=(
            "Return borrowing records available to the "
            "authenticated user.\n\n"
            "Regular users receive only their own borrowing "
            "records. The `user_id` parameter does not allow "
            "them to access another user's borrowings.\n\n"
            "Administrators receive borrowing records for "
            "all users. They can use the `user_id` parameter "
            "to return borrowings for a specific user.\n\n"
            "Use `is_active=true` to return borrowings that "
            "have not been returned yet. Use "
            "`is_active=false` to return borrowings that "
            "have already been returned."
        ),
        responses={
            200: BorrowingListSerializer(many=True),
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not "
                    "provided or the access token is invalid."
                ),
            ),
        },
    ),
    retrieve=extend_schema(
        tags=["Borrowings"],
        summary="Retrieve a borrowing",
        description=(
            "Return one borrowing record by its ID.\n\n"
            "Regular users can retrieve only their own "
            "borrowings. Administrators can retrieve any "
            "borrowing."
        ),
        responses={
            200: BorrowingDetailSerializer,
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not "
                    "provided or the access token is invalid."
                ),
            ),
            404: OpenApiResponse(
                description=(
                    "The borrowing does not exist or is not "
                    "available to the authenticated user."
                ),
            ),
        },
    ),
    create=extend_schema(
        tags=["Borrowings"],
        summary="Create a borrowing",
        description=(
            "Create a borrowing for the authenticated user "
            "and decrease the selected book inventory by "
            "one.\n\n"
            "The user, borrow date and actual return date "
            "are managed by the server and cannot be "
            "provided by the client."
        ),
        request=BorrowingCreateSerializer,
        responses={
            201: BorrowingDetailSerializer,
            400: OpenApiResponse(
                description=(
                    "Invalid borrowing data or the selected "
                    "book is unavailable."
                ),
            ),
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not "
                    "provided or the access token is invalid."
                ),
            ),
        },
    ),
)
class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.select_related(
        "book",
        "user",
    )
    permission_classes = [IsAuthenticated]
    filterset_class = BorrowingFilter


    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "create":
            return BorrowingCreateSerializer

        if self.action == "retrieve":
            return BorrowingDetailSerializer

        return BorrowingListSerializer

    def get_queryset(self) -> QuerySet[Borrowing]:
        queryset = super().get_queryset()

        if getattr(
            self,
            "swagger_fake_view",
            False,
        ):
            return queryset.none()

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(
            user=self.request.user,
        )

    def create(
        self,
        request: Request,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        borrowing = serializer.save(user=request.user)

        response_serializer = (
            BorrowingDetailSerializer(
                borrowing,
                context=self.get_serializer_context(),
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Borrowings"],
        summary="Return a borrowed book",
        description=(
            "Return a book for the selected borrowing.\n\n"
            "The endpoint sets the actual return date to the "
            "current date and increases the related book "
            "inventory by one.\n\n"
            "A borrowing cannot be returned more than once. "
            "Regular users can return only their own books. "
            "Admins can return any borrowing."
        ),
        request=None,
        responses={
            200: BorrowingDetailSerializer,
            400: OpenApiResponse(
                description=(
                        "The borrowing has already been returned."
                ),
            ),
            401: OpenApiResponse(
                description=(
                        "Authentication credentials were not "
                        "provided or the access token is invalid."
                ),
            ),
            404: OpenApiResponse(
                description=(
                        "The borrowing does not exist or is not "
                        "available to the authenticated user."
                ),
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="return",
        url_name="return",
    )
    def return_borrowing(
        self,
        request: Request,
        pk: int | None = None,
    ) -> Response:
        with transaction.atomic():
            borrowing_queryset = (
                self.get_queryset()
                .select_related(None)
                .select_for_update()
            )

            borrowing = get_object_or_404(
                borrowing_queryset,
                pk=pk,
            )

            if borrowing.actual_return_date is not None:
                raise ValidationError(
                    {
                        "actual_return_date": (
                            "This borrowing has already "
                            "been returned."
                        ),
                    }
                )

            locked_book = (
                Book.objects.select_for_update()
                .get(pk=borrowing.book_id)
            )

            borrowing.actual_return_date = (
                timezone.localdate()
            )
            borrowing.save(
                update_fields=[
                    "actual_return_date",
                ],
            )

            locked_book.inventory += 1
            locked_book.save(
                update_fields=["inventory"],
            )

            borrowing.book = locked_book

        response_serializer = (
            BorrowingDetailSerializer(
                borrowing,
                context=self.get_serializer_context(),
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
