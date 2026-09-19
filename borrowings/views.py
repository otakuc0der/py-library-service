from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingReadSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Borrowings"],
        summary="List borrowings",
        description=(
            "Return borrowing records available to the "
            "authenticated user. Regular users receive only "
            "their own borrowings. Administrators receive all "
            "borrowing records."
        ),
        responses={
            200: BorrowingReadSerializer(many=True),
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
            "Return one borrowing record by its ID. Regular "
            "users can retrieve only their own borrowings. "
            "Administrators can retrieve any borrowing."
        ),
        responses={
            200: BorrowingReadSerializer,
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
            "and decrease the selected book inventory by one."
        ),
        request=BorrowingCreateSerializer,
        responses={
            201: BorrowingReadSerializer,
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

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "create":
            return BorrowingCreateSerializer

        return BorrowingReadSerializer

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
        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        borrowing = serializer.save(
            user=request.user
        )

        response_serializer = (
            BorrowingReadSerializer(
                borrowing,
                context=self.get_serializer_context(),
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )
