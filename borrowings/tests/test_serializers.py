from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import serializers

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingReadSerializer,
)


class BorrowingSerializerTestBase(TestCase):
    def setUp(self) -> None:
        self.user = (
            get_user_model().objects.create_user(
                email="user@example.com",
                password="test-password",
            )
        )
        self.other_user = (
            get_user_model().objects.create_user(
                email="other@example.com",
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

    def get_create_data(
        self,
        **changes,
    ) -> dict:
        data = {
            "expected_return_date": (
                timezone.localdate()
                + timedelta(days=7)
            ).isoformat(),
            "book": self.book.id,
        }
        data.update(changes)

        return data


class BorrowingReadSerializerTests(
    BorrowingSerializerTestBase,
):
    def setUp(self) -> None:
        super().setUp()

        self.borrowing = Borrowing.objects.create(
            borrow_date=timezone.localdate(),
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
            actual_return_date=None,
            book=self.book,
            user=self.user,
        )

    def test_serializer_returns_all_fields(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            set(serializer.data.keys()),
            {
                "id",
                "borrow_date",
                "expected_return_date",
                "actual_return_date",
                "book",
                "user",
            },
        )

    def test_serializer_returns_nested_book(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertIsInstance(
            serializer.data["book"],
            dict,
        )

    def test_nested_book_contains_required_fields(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            set(serializer.data["book"].keys()),
            {
                "id",
                "title",
                "author",
                "cover",
                "inventory",
                "daily_fee",
            },
        )

    def test_nested_book_contains_correct_data(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )
        book_data = serializer.data["book"]

        self.assertEqual(
            book_data["id"],
            self.book.id,
        )
        self.assertEqual(
            book_data["title"],
            self.book.title,
        )
        self.assertEqual(
            book_data["author"],
            self.book.author,
        )
        self.assertEqual(
            book_data["cover"],
            self.book.cover,
        )
        self.assertEqual(
            book_data["inventory"],
            self.book.inventory,
        )

    def test_serializer_returns_user_id(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            serializer.data["user"],
            self.user.id,
        )

    def test_daily_fee_is_returned_as_string(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            serializer.data["book"]["daily_fee"],
            "2.30",
        )

    def test_actual_return_date_is_returned_as_null(
        self,
    ) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertIsNone(
            serializer.data["actual_return_date"]
        )

    def test_serializer_fields_are_read_only(
        self,
    ) -> None:
        original_expected_return_date = (
            self.borrowing.expected_return_date
        )

        serializer = BorrowingReadSerializer(
            instance=self.borrowing,
            data={
                "borrow_date": "2026-01-01",
                "expected_return_date": "2026-01-10",
                "actual_return_date": "2026-01-09",
                "book": self.book.id,
                "user": self.other_user.id,
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data,
            {},
        )

        borrowing = serializer.save()
        borrowing.refresh_from_db()

        self.assertEqual(
            borrowing.expected_return_date,
            original_expected_return_date,
        )
        self.assertIsNone(
            borrowing.actual_return_date,
        )
        self.assertEqual(
            borrowing.user,
            self.user,
        )


class BorrowingCreateSerializerTests(
    BorrowingSerializerTestBase,
):
    def test_valid_data_passes_validation(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_expected_return_date_can_equal_today(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data(
                expected_return_date=(
                    timezone.localdate().isoformat()
                ),
            )
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_past_expected_return_date_is_forbidden(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data(
                expected_return_date=(
                    timezone.localdate()
                    - timedelta(days=1)
                ).isoformat(),
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "expected_return_date",
            serializer.errors,
        )
        self.assertEqual(
            str(
                serializer.errors[
                    "expected_return_date"
                ][0]
            ),
            (
                "Expected return date cannot be "
                "earlier than borrow date."
            ),
        )

    def test_zero_inventory_is_forbidden(
        self,
    ) -> None:
        self.book.inventory = 0
        self.book.save(
            update_fields=["inventory"]
        )

        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "book",
            serializer.errors,
        )
        self.assertEqual(
            str(serializer.errors["book"][0]),
            "This book is currently unavailable.",
        )

    def test_book_is_required(self) -> None:
        data = self.get_create_data()
        data.pop("book")

        serializer = BorrowingCreateSerializer(
            data=data
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "book",
            serializer.errors,
        )

    def test_expected_return_date_is_required(
        self,
    ) -> None:
        data = self.get_create_data()
        data.pop("expected_return_date")

        serializer = BorrowingCreateSerializer(
            data=data
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "expected_return_date",
            serializer.errors,
        )

    def test_nonexistent_book_is_forbidden(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data(
                book=999_999,
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "book",
            serializer.errors,
        )

    def test_serializer_creates_borrowing(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )
        serializer.is_valid(
            raise_exception=True
        )

        borrowing = serializer.save(
            user=self.user
        )

        self.assertEqual(
            Borrowing.objects.count(),
            1,
        )
        self.assertEqual(
            borrowing.book,
            self.book,
        )

    def test_serializer_attaches_provided_user(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )
        serializer.is_valid(
            raise_exception=True
        )

        borrowing = serializer.save(
            user=self.user
        )

        self.assertEqual(
            borrowing.user,
            self.user,
        )

    def test_serializer_decreases_book_inventory(
        self,
    ) -> None:
        original_inventory = self.book.inventory

        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )
        serializer.is_valid(
            raise_exception=True
        )
        serializer.save(user=self.user)

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.inventory,
            original_inventory - 1,
        )

    def test_client_cannot_override_user(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data(
                user=self.other_user.id,
            )
        )
        serializer.is_valid(
            raise_exception=True
        )

        borrowing = serializer.save(
            user=self.user
        )

        self.assertEqual(
            borrowing.user,
            self.user,
        )

    def test_client_cannot_set_borrow_date(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data(
                borrow_date="2020-01-01",
            )
        )
        serializer.is_valid(
            raise_exception=True
        )

        borrowing = serializer.save(
            user=self.user
        )

        self.assertEqual(
            borrowing.borrow_date,
            timezone.localdate(),
        )

    def test_client_cannot_set_actual_return_date(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data(
                actual_return_date=(
                    timezone.localdate().isoformat()
                ),
            )
        )
        serializer.is_valid(
            raise_exception=True
        )

        borrowing = serializer.save(
            user=self.user
        )

        self.assertIsNone(
            borrowing.actual_return_date
        )

    @patch(
        "borrowings.serializers."
        "validate_book_inventory"
    )
    def test_inventory_is_checked_again_after_book_lock(
        self,
        mocked_validator,
    ) -> None:
        mocked_validator.side_effect = [
            None,
            "This book is currently unavailable.",
        ]

        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )
        serializer.is_valid(
            raise_exception=True
        )

        with self.assertRaises(
            serializers.ValidationError
        ):
            serializer.save(user=self.user)

        self.book.refresh_from_db()

        self.assertEqual(
            Borrowing.objects.count(),
            0,
        )
        self.assertEqual(
            self.book.inventory,
            12,
        )

    def test_creation_is_rolled_back_when_inventory_update_fails(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )
        serializer.is_valid(
            raise_exception=True
        )

        with patch.object(
            Book,
            "save",
            side_effect=RuntimeError(
                "Inventory update failed."
            ),
        ):
            with self.assertRaises(RuntimeError):
                serializer.save(user=self.user)

        self.book.refresh_from_db()

        self.assertEqual(
            Borrowing.objects.count(),
            0,
        )
        self.assertEqual(
            self.book.inventory,
            12,
        )
