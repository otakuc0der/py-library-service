from django.db.models import QuerySet
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from payments.models import Payment
from payments.serializers import PaymentSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Payments"],
        summary="List payments",
        description=(
            "Return payment records available to the "
            "authenticated user.\n\n"
            "Regular users receive only payments connected "
            "to their own borrowings.\n\n"
            "Administrators receive payment records for "
            "all users."
        ),
        responses={
            200: PaymentSerializer(many=True),
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not "
                    "provided or the access token is invalid."
                ),
            ),
        },
    ),
    retrieve=extend_schema(
        tags=["Payments"],
        summary="Retrieve a payment",
        description=(
            "Return one payment record by its ID.\n\n"
            "Regular users can retrieve only payments "
            "connected to their own borrowings. "
            "Administrators can retrieve any payment."
        ),
        responses={
            200: PaymentSerializer,
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not "
                    "provided or the access token is invalid."
                ),
            ),
            404: OpenApiResponse(
                description=(
                    "The payment does not exist or is not "
                    "available to the authenticated user."
                ),
            ),
        },
    ),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related(
        "borrowing",
        "borrowing__user",
    )
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Payment]:
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
            borrowing__user=self.request.user,
        )
