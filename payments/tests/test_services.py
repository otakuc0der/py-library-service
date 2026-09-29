from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    override_settings,
)

from books.models import Book
from borrowings.models import Borrowing
from payments.exceptions import (
    PaymentSessionMismatchError,
)
from payments.models import Payment
from payments.services import (
    create_checkout_payment,
    create_payment_for_borrowing,
    get_amount_in_cents,
    mark_payment_as_paid,
)


class PaymentCalculationServiceTests(SimpleTestCase):
    @override_settings(CENTS_PER_DOLLAR=100)
    def test_get_amount_in_cents_converts_dollars_to_cents(
        self,
    ) -> None:
        payment = Payment(
            money_to_pay=Decimal("12.50"),
        )

        amount = get_amount_in_cents(payment)

        self.assertEqual(amount, 1250)

    @patch("payments.services.create_checkout_payment")
    def test_create_payment_for_borrowing_calculates_rental_amount(
        self,
        mocked_create_checkout: MagicMock,
    ) -> None:
        borrowing = MagicMock(spec=Borrowing)
        borrowing.borrow_date = date(2026, 9, 10)
        borrowing.expected_return_date = date(
            2026,
            9,
            15,
        )

        borrowing.book = MagicMock()
        borrowing.book.daily_fee = Decimal("2.50")
        borrowing.book.title = "Test Book"

        request = MagicMock(spec=HttpRequest)
        expected_payment = MagicMock(spec=Payment)

        mocked_create_checkout.return_value = expected_payment

        result = create_payment_for_borrowing(
            borrowing=borrowing,
            request=request,
        )

        self.assertIs(result, expected_payment)
        mocked_create_checkout.assert_called_once_with(
            borrowing=borrowing,
            request=request,
            money_to_pay=Decimal("12.50"),
            payment_type=Payment.Type.PAYMENT,
            product_name=("Pay for borrowing " "the 'Test Book' book."),
        )

    @patch("payments.services.create_checkout_payment")
    def test_create_payment_for_borrowing_rejects_non_positive_rental_period(
        self,
        mocked_create_checkout: MagicMock,
    ) -> None:
        request = MagicMock(spec=HttpRequest)
        borrow_date = date(2026, 9, 10)

        invalid_expected_dates = [
            date(2026, 9, 10),
            date(2026, 9, 9),
        ]

        for expected_return_date in invalid_expected_dates:
            with self.subTest(
                expected_return_date=(expected_return_date),
            ):
                borrowing = MagicMock(spec=Borrowing)
                borrowing.borrow_date = borrow_date
                borrowing.expected_return_date = expected_return_date

                with self.assertRaisesMessage(
                    ValueError,
                    ("Expected return date must be " "after borrowing date."),
                ):
                    create_payment_for_borrowing(
                        borrowing=borrowing,
                        request=request,
                    )

        mocked_create_checkout.assert_not_called()

    def test_create_checkout_payment_rejects_non_positive_amount(
        self,
    ) -> None:
        borrowing = MagicMock(spec=Borrowing)
        request = MagicMock(spec=HttpRequest)

        invalid_amounts = [
            Decimal("0.00"),
            Decimal("-1.00"),
        ]

        for amount in invalid_amounts:
            with self.subTest(
                money_to_pay=amount,
            ):
                with self.assertRaisesMessage(
                    ValueError,
                    ("Payment amount must be " "greater than zero."),
                ):
                    create_checkout_payment(
                        borrowing=borrowing,
                        request=request,
                        payment_type=(Payment.Type.PAYMENT),
                        product_name=("Pay for 'Test' book"),
                        money_to_pay=amount,
                    )

        request.build_absolute_uri.assert_not_called()


class CheckoutPaymentCreationTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="checkout@example.com",
            password="test-password",
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("2.00"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=date(2026, 9, 1),
            expected_return_date=date(
                2026,
                9,
                10,
            ),
            actual_return_date=date(
                2026,
                9,
                15,
            ),
        )

        self.request = RequestFactory().post(
            "/api/payments/create/",
            HTTP_HOST="localhost",
        )

    @override_settings(CENTS_PER_DOLLAR=100)
    @patch("payments.services.get_stripe_client")
    def test_create_checkout_payment_creates_payment_and_stripe_session(
        self,
        mocked_get_stripe_client: MagicMock,
    ) -> None:
        mocked_session = MagicMock()
        mocked_session.id = "cs_test_created"
        mocked_session.url = "https://checkout.stripe.com/" "cs_test_created"

        stripe_create = (
            mocked_get_stripe_client.return_value.v1.checkout.sessions.create
        )
        stripe_create.return_value = mocked_session

        payment = create_checkout_payment(
            borrowing=self.borrowing,
            request=self.request,
            money_to_pay=Decimal("15.00"),
            payment_type=Payment.Type.FINE,
            product_name=("Overdue fine for Test Book"),
        )

        payment.refresh_from_db()

        self.assertEqual(
            Payment.objects.count(),
            1,
        )
        self.assertEqual(
            payment.borrowing_id,
            self.borrowing.id,
        )
        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )
        self.assertEqual(
            payment.type,
            Payment.Type.FINE,
        )
        self.assertEqual(
            payment.money_to_pay,
            Decimal("15.00"),
        )
        self.assertEqual(
            payment.session_id,
            "cs_test_created",
        )
        self.assertEqual(
            payment.session_url,
            ("https://checkout.stripe.com/" "cs_test_created"),
        )

        mocked_get_stripe_client.assert_called_once_with()
        stripe_create.assert_called_once()

        stripe_params = stripe_create.call_args.kwargs["params"]

        self.assertEqual(
            stripe_params["mode"],
            "payment",
        )
        self.assertEqual(
            stripe_params["client_reference_id"],
            str(payment.id),
        )
        self.assertEqual(
            stripe_params["line_items"][0]["price_data"]["currency"],
            "usd",
        )
        self.assertEqual(
            stripe_params["line_items"][0]["price_data"]["unit_amount"],
            1500,
        )
        self.assertEqual(
            stripe_params["line_items"][0]["price_data"]["product_data"]["name"],
            "Overdue fine for Test Book",
        )
        self.assertEqual(
            stripe_params["line_items"][0]["quantity"],
            1,
        )
        self.assertIn(
            "?session_id={CHECKOUT_SESSION_ID}",
            stripe_params["success_url"],
        )
        self.assertIn(
            "checkout/cancel",
            stripe_params["cancel_url"],
        )

class PaymentCompletionServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="payment@example.com",
            password="test-password",
        )

        self.book = Book.objects.create(
            title="Payment Test Book",
            author="Test Author",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("2.00"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=date(2026, 9, 1),
            expected_return_date=date(
                2026,
                9,
                10,
            ),
            actual_return_date=None,
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            status=Payment.Status.PENDING,
            type=Payment.Type.PAYMENT,
            session_url=("https://checkout.stripe.com/" "cs_test_payment"),
            session_id="cs_test_payment",
            money_to_pay=Decimal("20.00"),
        )

    def create_valid_session(self) -> MagicMock:
        session = MagicMock()
        session.id = self.payment.session_id
        session.client_reference_id = str(self.payment.id)
        session.payment_status = "paid"
        session.amount_total = 2000
        session.currency = "usd"

        return session

    @override_settings(CENTS_PER_DOLLAR=100)
    @patch("payments.services." "send_payment_completed_notification.delay")
    def test_mark_payment_as_paid_updates_status_and_queues_notification(
        self,
        mocked_delay: MagicMock,
    ) -> None:
        session = self.create_valid_session()

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            mark_payment_as_paid(session)

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PAID,
        )
        self.assertEqual(len(callbacks), 1)
        mocked_delay.assert_called_once_with(self.payment.id)

    @override_settings(CENTS_PER_DOLLAR=100)
    @patch("payments.services." "send_payment_completed_notification.delay")
    def test_mark_payment_as_paid_is_idempotent_for_paid_payment(
        self,
        mocked_delay: MagicMock,
    ) -> None:
        self.payment.status = Payment.Status.PAID
        self.payment.save(update_fields=["status"])

        session = self.create_valid_session()

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            mark_payment_as_paid(session)

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PAID,
        )
        self.assertEqual(len(callbacks), 0)
        mocked_delay.assert_not_called()

    @override_settings(CENTS_PER_DOLLAR=100)
    @patch("payments.services." "send_payment_completed_notification.delay")
    def test_mark_payment_as_paid_rejects_mismatched_session(
        self,
        mocked_delay: MagicMock,
    ) -> None:
        mismatches = [
            (
                "client_reference_id",
                "different-payment-id",
            ),
            (
                "payment_status",
                "unpaid",
            ),
            (
                "amount_total",
                1900,
            ),
            (
                "currency",
                "eur",
            ),
        ]

        for attribute, invalid_value in mismatches:
            with self.subTest(
                attribute=attribute,
                invalid_value=invalid_value,
            ):
                session = self.create_valid_session()
                setattr(
                    session,
                    attribute,
                    invalid_value,
                )

                with self.assertRaisesMessage(
                    PaymentSessionMismatchError,
                    ("Stripe Session does not " "match the payment."),
                ):
                    mark_payment_as_paid(session)

                self.payment.refresh_from_db()

                self.assertEqual(
                    self.payment.status,
                    Payment.Status.PENDING,
                )

        mocked_delay.assert_not_called()
