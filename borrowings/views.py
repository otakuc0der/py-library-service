from django.db.models import QuerySet

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from borrowings.models import Borrowing
from borrowings.serializers import BorrowingReadSerializer


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
)
class BorrowingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BorrowingReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Borrowing]:
        queryset = Borrowing.objects.select_related(
            "book",
            "user",
        )

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(
            user=self.request.user,
        )
