from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from payments.models import Payment
from payments.serializers import PaymentSerializer


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
