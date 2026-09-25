from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.views import (
    PaymentViewSet,
    checkout_cancel,
    checkout_success,
)


router = DefaultRouter()
router.register(
    "",
    PaymentViewSet,
    basename="payment",
)

app_name = "payments"

urlpatterns = [
    path(
        "checkout/success/",
        checkout_success,
        name="checkout-success",
    ),
    path(
        "checkout/cancel/",
        checkout_cancel,
        name="checkout-cancel",
    ),
    path("", include(router.urls)),
]
