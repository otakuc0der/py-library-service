import stripe

from django.conf import settings
from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from payments.exceptions import PaymentSessionMismatchError
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import mark_payment_as_paid
from payments.stripe_client import get_stripe_client


payment_status_response = inline_serializer(
    name="CheckoutSuccessResponse",
    fields={
        "status": serializers.CharField(),
        "message": serializers.CharField(),
    },
)

payment_message_response = inline_serializer(
    name="CheckoutMessageResponse",
    fields={
        "message": serializers.CharField(),
    },
)

payment_cancel_response = inline_serializer(
    name="CheckoutCancelResponse",
    fields={
        "status": serializers.CharField(),
        "message": serializers.CharField(),
    },
)


@extend_schema_view(
    list=extend_schema(
        tags=["Payments"],
        summary="List payments",
        description=(
            "Return payment records available to the "
            "authenticated user.\n\n"
            "Regular users receive only payments connected "
            "to their own borrowings. Administrators receive "
            "payment records for all users."
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
        "borrowing__book",
    )
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Payment]:
        queryset = super().get_queryset()

        if getattr(self, "swagger_fake_view", False):
            return queryset.none()

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(
            borrowing__user=self.request.user
        )

    @extend_schema(
        tags=["Payments"],
        summary="Handle a Stripe webhook",
        description=(
            "Receive an event from Stripe and verify its "
            "signature using the webhook secret.\n\n"
            "When a `checkout.session.completed` event reports "
            "`payment_status=paid`, verify that the Checkout "
            "Session matches the stored payment and mark the "
            "payment as paid.\n\n"
            "Other valid events are acknowledged without "
            "changing a payment. This endpoint is called by "
            "Stripe and does not require user authentication."
        ),
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiResponse(
                description=(
                    "The event was accepted. Relevant payment "
                    "changes have been processed."
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "The payload or signature is invalid, or "
                    "the Checkout Session does not match the "
                    "stored payment."
                ),
            ),
            503: OpenApiResponse(
                description=(
                    "A payment for the verified Checkout "
                    "Session was not found. Stripe can retry "
                    "the event."
                ),
            ),
        },
        auth=[],
    )
    @action(
        methods=["post"],
        detail=False,
        permission_classes=[],
        authentication_classes=[],
        url_path="stripe/webhook",
    )
    def event_handler(self, request: Request) -> Response:
        body = request._request.body
        signature = request.headers.get("Stripe-Signature")

        try:
            event = get_stripe_client().construct_event(
                body,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            event.type == "checkout.session.completed"
            and event.data.object.payment_status == "paid"
        ):
            try:
                mark_payment_as_paid(event.data.object)
            except Payment.DoesNotExist:
                return Response(
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except PaymentSessionMismatchError:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(status=status.HTTP_200_OK)


@extend_schema(
    tags=["Payments"],
    summary="Check Checkout payment status",
    description=(
        "Return the stored payment status for a Checkout "
        "Session after Stripe redirects the customer here.\n\n"
        "This endpoint only reads the payment status. "
        "A verified Stripe webhook is responsible for "
        "marking the payment as paid. The response can "
        "temporarily be `pending` while the webhook is "
        "being processed."
    ),
    parameters=[
        OpenApiParameter(
            name="session_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Checkout Session ID inserted into the "
                "success URL by Stripe."
            ),
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=payment_status_response,
            description=(
                "The payment was found. Its status is "
                "`paid` or `pending`."
            ),
        ),
        400: OpenApiResponse(
            response=payment_message_response,
            description="The session_id parameter is missing.",
        ),
        404: OpenApiResponse(
            response=payment_message_response,
            description=(
                "No payment was found for this Checkout "
                "Session."
            ),
        ),
    },
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def checkout_success(request: Request) -> Response:
    session_id = request.query_params.get("session_id")

    if not session_id:
        return Response(
            {"message": "The payment session ID is missing."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payment = Payment.objects.filter(
        session_id=session_id,
    ).first()

    if payment is None:
        return Response(
            {
                "message": (
                    "We could not find a payment for this session."
                )
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if payment.status == Payment.Status.PAID:
        return Response({
            "status": payment.status,
            "message": (
                "Thank you. Your payment has been received."
            ),
        })

    return Response({
        "status": payment.status,
        "message": (
            "Your payment has not been confirmed yet. "
            "Please check its status later."
        ),
    })


@extend_schema(
    tags=["Payments"],
    summary="Return from Checkout without paying",
    description=(
        "Return a message when the customer leaves the "
        "Stripe Checkout page without completing payment.\n\n"
        "Opening this endpoint does not change the stored "
        "payment status. The customer may try again while "
        "the Checkout Session remains available."
    ),
    responses={
        200: OpenApiResponse(
            response=payment_cancel_response,
            description=(
                "Checkout was left without completing payment."
            ),
        ),
    },
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def checkout_cancel(request: Request) -> Response:
    return Response({
        "status": "cancelled",
        "message": (
            "Payment was not completed. You can try again later "
            "if the checkout session is still available."
        ),
    })
