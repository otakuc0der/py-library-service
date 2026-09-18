from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing


class BorrowingModelTests(TestCase):
    def setUp(self) -> None:
        self.user = (
            get_user_model().objects.create_user(
                email="user@example.com",
                password="test-password",
            )
        )
        self.book = Book.objects.create(
            title="The Little Prince",
            author="Antoine de Saint-Exupéry",
            cover=Book.Cover.HARD,
            inventory=12,
            daily_fee=Decimal("2.30"),
        )

    def get_borrowing_data(
        self,
        **changes,
    ) -> dict:
        borrow_date = timezone.localdate()

        borrowing_data = {
            "borrow_date": borrow_date,
            "expected_return_date": (
                borrow_date + timedelta(days=7)
            ),
            "actual_return_date": None,
            "book": self.book,
            "user": self.user,
        }
        borrowing_data.update(changes)

        return borrowing_data

    def test_create_borrowing_with_correct_data(self) -> None:
        borrowing_data = self.get_borrowing_data()

        borrowing = Borrowing.objects.create(
            **borrowing_data
        )

        self.assertEqual(
            borrowing.borrow_date,
            borrowing_data["borrow_date"],
        )
        self.assertEqual(
            borrowing.expected_return_date,
            borrowing_data[
                "expected_return_date"
            ],
        )
        self.assertIsNone(
            borrowing.actual_return_date
        )
        self.assertEqual(
            borrowing.book,
            self.book,
        )
        self.assertEqual(
            borrowing.user,
            self.user,
        )

    def test_borrow_date_is_filled_automatically(self) -> None:
        borrowing = Borrowing.objects.create(
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
            book=self.book,
            user=self.user,
        )

        self.assertEqual(
            borrowing.borrow_date,
            timezone.localdate(),
        )

    def test_actual_return_date_can_be_none(self) -> None:
        borrowing = Borrowing.objects.create(
            **self.get_borrowing_data(
                actual_return_date=None,
            )
        )

        self.assertIsNone(
            borrowing.actual_return_date
        )

    def test_expected_return_date_can_equal_borrow_date(self) -> None:
        borrow_date = timezone.localdate()
        borrowing = Borrowing(
            **self.get_borrowing_data(
                borrow_date=borrow_date,
                expected_return_date=borrow_date,
            )
        )

        borrowing.full_clean()

    def test_expected_return_before_borrow_date_fails_validation(
        self,
    ) -> None:
        borrow_date = timezone.localdate()
        borrowing = Borrowing(
            **self.get_borrowing_data(
                borrow_date=borrow_date,
                expected_return_date=(
                    borrow_date - timedelta(days=1)
                ),
            )
        )

        with self.assertRaises(
            ValidationError
        ) as error:
            borrowing.full_clean()

        self.assertIn(
            "expected_return_date",
            error.exception.message_dict,
        )

    def test_actual_return_before_borrow_date_fails_validation(
        self,
    ) -> None:
        borrow_date = timezone.localdate()
        borrowing = Borrowing(
            **self.get_borrowing_data(
                borrow_date=borrow_date,
                actual_return_date=(
                    borrow_date - timedelta(days=1)
                ),
            )
        )

        with self.assertRaises(
            ValidationError
        ) as error:
            borrowing.full_clean()

        self.assertIn(
            "actual_return_date",
            error.exception.message_dict,
        )

    def test_actual_return_date_can_be_after_expected_return_date(
        self,
    ) -> None:
        borrow_date = timezone.localdate()
        expected_return_date = (
            borrow_date + timedelta(days=7)
        )
        borrowing = Borrowing(
            **self.get_borrowing_data(
                borrow_date=borrow_date,
                expected_return_date=(
                    expected_return_date
                ),
                actual_return_date=(
                    expected_return_date
                    + timedelta(days=3)
                ),
            )
        )

        borrowing.full_clean()

    def test_str_returns_user_and_book(self) -> None:
        borrowing = Borrowing.objects.create(
            **self.get_borrowing_data()
        )

        self.assertEqual(
            str(borrowing),
            (
                f"{self.user} borrowed "
                f"{self.book}"
            ),
        )

    def test_borrowings_are_ordered_by_date_and_id(self) -> None:
        today = timezone.localdate()

        oldest_borrowing = (
            Borrowing.objects.create(
                **self.get_borrowing_data(
                    borrow_date=(
                        today - timedelta(days=2)
                    ),
                    expected_return_date=(
                        today + timedelta(days=5)
                    ),
                )
            )
        )
        first_newest_borrowing = (
            Borrowing.objects.create(
                **self.get_borrowing_data(
                    borrow_date=today,
                    expected_return_date=(
                        today + timedelta(days=7)
                    ),
                )
            )
        )
        second_newest_borrowing = (
            Borrowing.objects.create(
                **self.get_borrowing_data(
                    borrow_date=today,
                    expected_return_date=(
                        today + timedelta(days=10)
                    ),
                )
            )
        )

        self.assertQuerySetEqual(
            Borrowing.objects.all(),
            [
                second_newest_borrowing,
                first_newest_borrowing,
                oldest_borrowing,
            ],
        )

    def test_borrowing_is_connected_to_book(self) -> None:
        borrowing = Borrowing.objects.create(
            **self.get_borrowing_data()
        )

        self.assertEqual(
            borrowing.book,
            self.book,
        )
        self.assertIn(
            borrowing,
            self.book.borrowings.all(),
        )

    def test_borrowing_is_connected_to_user(self) -> None:
        borrowing = Borrowing.objects.create(
            **self.get_borrowing_data()
        )

        self.assertEqual(
            borrowing.user,
            self.user,
        )
        self.assertIn(
            borrowing,
            self.user.borrowings.all(),
        )

    def test_expected_return_before_borrow_date_fails_database_constraint(
        self,
    ) -> None:
        borrow_date = date(2026, 9, 18)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Borrowing.objects.create(
                    **self.get_borrowing_data(
                        borrow_date=borrow_date,
                        expected_return_date=(
                            borrow_date
                            - timedelta(days=1)
                        ),
                    )
                )

    def test_actual_return_before_borrow_date_fails_database_constraint(
        self,
    ) -> None:
        borrow_date = date(2026, 9, 18)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Borrowing.objects.create(
                    **self.get_borrowing_data(
                        borrow_date=borrow_date,
                        expected_return_date=(
                            borrow_date
                            + timedelta(days=7)
                        ),
                        actual_return_date=(
                            borrow_date
                            - timedelta(days=1)
                        ),
                    )
                )
