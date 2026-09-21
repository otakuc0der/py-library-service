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
    BorrowingDetailSerializer,
    BorrowingListSerializer,
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


class BorrowingListSerializerTests(
    BorrowingSerializerTestBase
):
    def test_serializer_returns_all_fields(
        self,
    ) -> None:
        serializer = BorrowingListSerializer(
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

    def test_serializer_returns_brief_book(
        self,
    ) -> None:
        serializer = BorrowingListSerializer(
            self.borrowing
        )

        self.assertEqual(
            set(serializer.data["book"].keys()),
            {
                "id",
                "title",
                "author",
            },
        )

    def test_brief_book_contains_correct_data(
        self,
    ) -> None:
        book_data = BorrowingListSerializer(
            self.borrowing
        ).data["book"]

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

    def test_serializer_returns_brief_user(self) -> None:
        user_data = BorrowingListSerializer(
            self.borrowing
        ).data["user"]

        self.assertEqual(
            set(user_data.keys()),
            {
                "id",
                "email",
            },
        )
        self.assertEqual(
            user_data["id"],
            self.user.id,
        )
        self.assertEqual(
            user_data["email"],
            self.user.email,
        )

    def test_actual_return_date_is_null_for_active_borrowing(
        self,
    ) -> None:
        serializer = BorrowingListSerializer(
            self.borrowing
        )

        self.assertIsNone(
            serializer.data["actual_return_date"]
        )

    def test_all_fields_are_read_only(self) -> None:
        original_expected_return_date = (
            self.borrowing.expected_return_date
        )

        serializer = BorrowingListSerializer(
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

        serializer.save()
        self.borrowing.refresh_from_db()

        self.assertEqual(
            self.borrowing.expected_return_date,
            original_expected_return_date,
        )
        self.assertIsNone(
            self.borrowing.actual_return_date
        )
        self.assertEqual(
            self.borrowing.user,
            self.user,
        )


class BorrowingDetailSerializerTests(
    BorrowingSerializerTestBase
):
    def test_detail_serializer_returns_full_book(
        self,
    ) -> None:
        serializer = BorrowingDetailSerializer(
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

    def test_detail_serializer_returns_correct_book_data(
        self,
    ) -> None:
        book_data = BorrowingDetailSerializer(
            self.borrowing
        ).data["book"]

        self.assertEqual(
            book_data["id"],
            self.book.id,
        )
        self.assertEqual(
            book_data["cover"],
            self.book.cover,
        )
        self.assertEqual(
            book_data["inventory"],
            self.book.inventory,
        )
        self.assertEqual(
            book_data["daily_fee"],
            "2.30",
        )

    def test_detail_serializer_returns_brief_user(
        self,
    ) -> None:
        user_data = BorrowingDetailSerializer(
            self.borrowing
        ).data["user"]

        self.assertEqual(
            user_data,
            {
                "id": self.user.id,
                "email": self.user.email,
            },
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

    def test_serializer_creates_borrowing_for_user(
        self,
    ) -> None:
        initial_count = Borrowing.objects.count()

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
            initial_count + 1,
        )
        self.assertEqual(
            borrowing.user,
            self.user,
        )
        self.assertEqual(
            borrowing.book,
            self.book,
        )

    def test_serializer_decreases_inventory(
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

    @patch(
        "borrowings.serializers."
        "validate_book_inventory"
    )
    def test_inventory_is_checked_again_after_lock(
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

        initial_count = Borrowing.objects.count()

        with self.assertRaises(
            serializers.ValidationError
        ):
            serializer.save(user=self.user)

        self.book.refresh_from_db()

        self.assertEqual(
            Borrowing.objects.count(),
            initial_count,
        )
        self.assertEqual(
            self.book.inventory,
            12,
        )

    def test_transaction_is_rolled_back_when_inventory_update_fails(
        self,
    ) -> None:
        serializer = BorrowingCreateSerializer(
            data=self.get_create_data()
        )
        serializer.is_valid(
            raise_exception=True
        )

        initial_count = Borrowing.objects.count()

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
            initial_count,
        )
        self.assertEqual(
            self.book.inventory,
            12,
        )
