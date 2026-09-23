from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


class PaymentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )

        cls.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            cover="soft",
            inventory=5,
            daily_fee=Decimal("2.50"),
        )

        cls.borrowing = Borrowing.objects.create(
            user=cls.user,
            book=cls.book,
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
        )

    def test_payment_uses_expected_defaults(self) -> None:
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url=(
                "https://checkout.stripe.com/"
                "test-session"
            ),
            session_id="cs_test_defaults",
            money_to_pay=Decimal("12.50"),
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )
        self.assertEqual(
            payment.type,
            Payment.Type.PAYMENT,
        )

    def test_payment_is_connected_to_borrowing(self) -> None:
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url=(
                "https://checkout.stripe.com/"
                "related-session"
            ),
            session_id="cs_test_relationship",
            money_to_pay=Decimal("15.00"),
        )

        self.assertEqual(
            payment.borrowing,
            self.borrowing,
        )
        self.assertIn(
            payment,
            self.borrowing.payments.all(),
        )

    def test_payment_string_representation(self) -> None:
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            session_url=(
                "https://checkout.stripe.com/"
                "string-session"
            ),
            session_id="cs_test_string",
            money_to_pay=Decimal("20.00"),
        )

        self.assertEqual(
            str(payment),
            (
                f"Payment payment #{payment.pk} "
                "— Pending"
            ),
        )

    def test_money_to_pay_cannot_be_negative(self) -> None:
        payment = Payment(
            borrowing=self.borrowing,
            session_url=(
                "https://checkout.stripe.com/"
                "invalid-session"
            ),
            session_id="cs_test_negative",
            money_to_pay=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_session_id_must_be_unique(self) -> None:
        Payment.objects.create(
            borrowing=self.borrowing,
            session_url=(
                "https://checkout.stripe.com/"
                "first-session"
            ),
            session_id="cs_test_unique",
            money_to_pay=Decimal("10.00"),
        )

        duplicate_payment = Payment(
            borrowing=self.borrowing,
            session_url=(
                "https://checkout.stripe.com/"
                "second-session"
            ),
            session_id="cs_test_unique",
            money_to_pay=Decimal("15.00"),
        )

        with self.assertRaises(ValidationError):
            duplicate_payment.full_clean()
