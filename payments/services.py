from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from rest_framework.request import Request

from borrowings.models import Borrowing
from notifications.tasks import send_payment_completed_notification
from payments.exceptions import PaymentSessionMismatchError
from payments.models import Payment
from payments.stripe_client import get_stripe_client


def get_amount_in_cents(payment: Payment) -> int:
    return int(payment.money_to_pay * settings.CENTS_PER_DOLLAR)


def create_checkout_payment(
    *,
    borrowing: Borrowing,
    request: Request,
    money_to_pay: Decimal,
    payment_type: Payment.Type,
    product_name: str,
) -> Payment:
    if money_to_pay <= Decimal("0.00"):
        raise ValueError("Payment amount must be greater than zero.")

    success_url = request.build_absolute_uri(
        reverse("payments:checkout-success"),
    )
    cancel_url = request.build_absolute_uri(
        reverse("payments:checkout-cancel"),
    )

    with transaction.atomic():
        payment = Payment.objects.create(
            borrowing=borrowing,
            type=payment_type,
            money_to_pay=money_to_pay,
        )

        session = (
            get_stripe_client()
            .v1.checkout.sessions.create(
                params={
                    "line_items": [
                        {
                            "price_data": {
                                "currency": "usd",
                                "unit_amount": (
                                    get_amount_in_cents(payment)
                                ),
                                "product_data": {
                                    "name": product_name,
                                },
                            },
                            "quantity": 1,
                        },
                    ],
                    "client_reference_id": str(
                        payment.id,
                    ),
                    "mode": "payment",
                    "success_url": (
                        f"{success_url}"
                        f"?session_id={{CHECKOUT_SESSION_ID}}"
                    ),
                    "cancel_url": cancel_url,
                },
            )
        )

        payment.session_id = session.id
        payment.session_url = session.url
        payment.save(
            update_fields=[
                "session_id",
                "session_url",
            ],
        )

    return payment


def create_payment_for_borrowing(
    borrowing: Borrowing,
    request: Request,
) -> Payment:
    rental_days = (
        borrowing.expected_return_date
        - borrowing.borrow_date
    ).days

    if rental_days <= 0:
        raise ValueError(
            "Expected return date must be after "
            "borrowing date."
        )

    money_to_pay = borrowing.book.daily_fee * rental_days

    return create_checkout_payment(
        borrowing=borrowing,
        request=request,
        money_to_pay=money_to_pay,
        payment_type=Payment.Type.PAYMENT,
        product_name=(
            "Pay for borrowing "
            f"the '{borrowing.book.title}' book."
        ),
    )


def mark_payment_as_paid(session) -> None:
    with transaction.atomic():
        payment = (
            Payment.objects
            .select_for_update()
            .get(session_id=session.id)
        )

        if (
            str(payment.id) != str(session.client_reference_id)
            or session.payment_status != "paid"
            or session.amount_total != get_amount_in_cents(payment)
            or session.currency != "usd"
        ):
            raise PaymentSessionMismatchError(
                "Stripe Session does not match the payment."
            )

        if payment.status == Payment.Status.PAID:
            return

        payment.status = Payment.Status.PAID
        payment.save(update_fields=["status"])

        payment_id = payment.id

        transaction.on_commit(
            lambda: send_payment_completed_notification.delay(
                payment_id
            )
        )
