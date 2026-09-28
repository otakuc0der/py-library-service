from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing
from payments.exceptions import PaymentSessionMismatchError
from payments.models import Payment


class PaymentViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )
        cls.another_user = (
            get_user_model().objects.create_user(
                email="another@example.com",
                password="test-password",
            )
        )
        cls.admin = (
            get_user_model().objects.create_superuser(
                email="admin@example.com",
                password="admin-password",
            )
        )

        cls.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            cover="soft",
            inventory=10,
            daily_fee=Decimal("2.50"),
        )

        cls.user_borrowing = Borrowing.objects.create(
            user=cls.user,
            book=cls.book,
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
        )
        cls.another_user_borrowing = (
            Borrowing.objects.create(
                user=cls.another_user,
                book=cls.book,
                expected_return_date=(
                    timezone.localdate()
                    + timedelta(days=10)
                ),
            )
        )

        cls.user_payment = Payment.objects.create(
            borrowing=cls.user_borrowing,
            status=Payment.Status.PENDING,
            type=Payment.Type.PAYMENT,
            session_url=(
                "https://checkout.stripe.com/"
                "user-session"
            ),
            session_id="cs_test_user",
            money_to_pay=Decimal("12.50"),
        )
        cls.another_user_payment = (
            Payment.objects.create(
                borrowing=(
                    cls.another_user_borrowing
                ),
                status=Payment.Status.PAID,
                type=Payment.Type.FINE,
                session_url=(
                    "https://checkout.stripe.com/"
                    "another-session"
                ),
                session_id="cs_test_another",
                money_to_pay=Decimal("25.00"),
            )
        )

        cls.list_url = reverse(
            "payments:payment-list",
        )

    def test_unauthenticated_user_cannot_list_payments(
        self,
    ) -> None:
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_retrieve_payment(
        self,
    ) -> None:
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_regular_user_sees_only_own_payments(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            payment["id"]
            for payment in response.data
        }

        self.assertEqual(
            returned_ids,
            {self.user_payment.id},
        )

    def test_regular_user_can_retrieve_own_payment(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.user_payment.id,
        )

    def test_regular_user_cannot_retrieve_another_users_payment(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.another_user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_sees_all_payments(self) -> None:
        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            payment["id"]
            for payment in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                self.user_payment.id,
                self.another_user_payment.id,
            },
        )

    def test_admin_can_retrieve_any_payment(self) -> None:
        self.client.force_authenticate(
            user=self.admin,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.another_user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.another_user_payment.id,
        )

    def test_payment_response_contains_expected_fields(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            set(response.data),
            {
                "id",
                "status",
                "type",
                "borrowing",
                "session_url",
                "session_id",
                "money_to_pay",
            },
        )

    def test_payment_endpoints_do_not_allow_write_methods(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        requests = [
            (
                self.client.post,
                self.list_url,
            ),
            (
                self.client.put,
                detail_url,
            ),
            (
                self.client.patch,
                detail_url,
            ),
            (
                self.client.delete,
                detail_url,
            ),
        ]

        for request_method, url in requests:
            with self.subTest(method=request_method.__name__):
                response = request_method(
                    url,
                    data={},
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )


class CheckoutResultViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = (
            get_user_model().objects.create_user(
                email="checkout@example.com",
                password="test-password",
            )
        )

        cls.book = Book.objects.create(
            title="Checkout Book",
            author="Test Author",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("2.00"),
        )

        cls.borrowing = Borrowing.objects.create(
            user=cls.user,
            book=cls.book,
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
        )

        cls.pending_payment = Payment.objects.create(
            borrowing=cls.borrowing,
            status=Payment.Status.PENDING,
            type=Payment.Type.PAYMENT,
            session_url=(
                "https://checkout.stripe.com/"
                "pending"
            ),
            session_id="cs_test_pending",
            money_to_pay=Decimal("14.00"),
        )

        cls.paid_payment = Payment.objects.create(
            borrowing=cls.borrowing,
            status=Payment.Status.PAID,
            type=Payment.Type.PAYMENT,
            session_url=(
                "https://checkout.stripe.com/"
                "paid"
            ),
            session_id="cs_test_paid",
            money_to_pay=Decimal("14.00"),
        )

        cls.success_url = reverse(
            "payments:checkout-success"
        )
        cls.cancel_url = reverse(
            "payments:checkout-cancel"
        )

    def test_checkout_success_requires_session_id(
        self,
    ) -> None:
        response = self.client.get(self.success_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data,
            {
                "message": (
                    "The payment session ID "
                    "is missing."
                )
            },
        )

    def test_checkout_success_returns_not_found_for_unknown_session(
        self,
    ) -> None:
        response = self.client.get(
            self.success_url,
            {
                "session_id": (
                    "cs_test_unknown"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data,
            {
                "message": (
                    "We could not find a payment "
                    "for this session."
                )
            },
        )

    def test_checkout_success_returns_stored_payment_status(
        self,
    ) -> None:
        expected_results = [
            (
                self.pending_payment,
                (
                    "Your payment has not been "
                    "confirmed yet. Please check "
                    "its status later."
                ),
            ),
            (
                self.paid_payment,
                (
                    "Thank you. Your payment "
                    "has been received."
                ),
            ),
        ]

        for payment, expected_message in expected_results:
            with self.subTest(payment_status=payment.status):
                response = self.client.get(
                    self.success_url,
                    {
                        "session_id": (
                            payment.session_id
                        ),
                    },
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    response.data,
                    {
                        "status": payment.status,
                        "message": expected_message,
                    },
                )

    def test_checkout_cancel_returns_message_without_changing_payment(
        self,
    ) -> None:
        original_status = self.pending_payment.status

        response = self.client.get(self.cancel_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "status": "cancelled",
                "message": (
                    "Payment was not completed. "
                    "You can try again later if "
                    "the checkout session is still "
                    "available."
                ),
            },
        )

        self.pending_payment.refresh_from_db()

        self.assertEqual(
            self.pending_payment.status,
            original_status,
        )


class StripeWebhookTests(APITestCase):
    def setUp(self) -> None:
        self.webhook_url = reverse(
            "payments:payment-event-handler"
        )

    @staticmethod
    def create_event(
        *,
        event_type: str = "checkout.session.completed",
        payment_status: str = "paid",
    ) -> tuple[MagicMock, MagicMock]:
        session = MagicMock()
        session.payment_status = payment_status

        event = MagicMock()
        event.type = event_type
        event.data.object = session

        return event, session

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    @patch("payments.views.mark_payment_as_paid")
    @patch("payments.views.get_stripe_client")
    def test_webhook_processes_completed_paid_session(
        self,
        mocked_get_stripe_client: MagicMock,
        mocked_mark_as_paid: MagicMock,
    ) -> None:
        event, session = self.create_event()

        mocked_construct_event = (
            mocked_get_stripe_client
            .return_value
            .construct_event
        )
        mocked_construct_event.return_value = event

        response = self.client.post(
            self.webhook_url,
            data={"id": "evt_test"},
            format="json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mocked_construct_event.assert_called_once()

        construct_arguments = mocked_construct_event.call_args.args

        self.assertIsInstance(
            construct_arguments[0],
            bytes,
        )
        self.assertEqual(
            construct_arguments[1],
            "test-signature",
        )
        self.assertEqual(
            construct_arguments[2],
            "whsec_test",
        )

        mocked_mark_as_paid.assert_called_once_with(session)

    @patch("payments.views.mark_payment_as_paid")
    @patch("payments.views.get_stripe_client")
    def test_webhook_rejects_invalid_payload_or_signature(
        self,
        mocked_get_stripe_client: MagicMock,
        mocked_mark_as_paid: MagicMock,
    ) -> None:
        (
            mocked_get_stripe_client
            .return_value
            .construct_event
            .side_effect
        ) = ValueError("Invalid payload")

        response = self.client.post(
            self.webhook_url,
            data={"invalid": "payload"},
            format="json",
            HTTP_STRIPE_SIGNATURE="invalid",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        mocked_mark_as_paid.assert_not_called()

    @patch("payments.views.mark_payment_as_paid")
    @patch("payments.views.get_stripe_client")
    def test_webhook_ignores_events_that_do_not_confirm_payment(
        self,
        mocked_get_stripe_client: MagicMock,
        mocked_mark_as_paid: MagicMock,
    ) -> None:
        ignored_events = [
            self.create_event(
                event_type="checkout.session.expired",
                payment_status="unpaid",
            )[0],
            self.create_event(
                payment_status="unpaid",
            )[0],
        ]

        mocked_construct_event = (
            mocked_get_stripe_client
            .return_value
            .construct_event
        )

        for event in ignored_events:
            with self.subTest(
                event_type=event.type,
                payment_status=(
                    event.data.object.payment_status
                ),
            ):
                mocked_construct_event.return_value = event

                response = self.client.post(
                    self.webhook_url,
                    data={"id": "evt_test"},
                    format="json",
                    HTTP_STRIPE_SIGNATURE=(
                        "test-signature"
                    ),
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )

        mocked_mark_as_paid.assert_not_called()

    @patch("payments.views.mark_payment_as_paid")
    @patch("payments.views.get_stripe_client")
    def test_webhook_returns_service_unavailable_when_payment_is_missing(
        self,
        mocked_get_stripe_client: MagicMock,
        mocked_mark_as_paid: MagicMock,
    ) -> None:
        event, _ = self.create_event()

        (
            mocked_get_stripe_client
            .return_value
            .construct_event
            .return_value
        ) = event

        mocked_mark_as_paid.side_effect = (
            Payment.DoesNotExist
        )

        response = self.client.post(
            self.webhook_url,
            data={"id": "evt_test"},
            format="json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @patch("payments.views.mark_payment_as_paid")
    @patch("payments.views.get_stripe_client")
    def test_webhook_rejects_mismatched_payment_session(
        self,
        mocked_get_stripe_client: MagicMock,
        mocked_mark_as_paid: MagicMock,
    ) -> None:
        event, _ = self.create_event()

        (
            mocked_get_stripe_client
            .return_value
            .construct_event
            .return_value
        ) = event

        mocked_mark_as_paid.side_effect = (
            PaymentSessionMismatchError(
                (
                    "Stripe Session does not "
                    "match the payment."
                )
            )
        )

        response = self.client.post(
            self.webhook_url,
            data={"id": "evt_test"},
            format="json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
