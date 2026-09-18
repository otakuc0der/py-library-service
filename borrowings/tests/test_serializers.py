from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingReadSerializer,
)


class BorrowingReadSerializerTests(TestCase):
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

    def test_serializer_returns_all_fields(self) -> None:
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

    def test_serializer_returns_nested_book(self) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertIsInstance(
            serializer.data["book"],
            dict,
        )

    def test_nested_book_contains_required_fields(self) -> None:
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

    def test_nested_book_contains_correct_data(self) -> None:
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

    def test_serializer_returns_user_id(self) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            serializer.data["user"],
            self.user.id,
        )

    def test_daily_fee_is_returned_as_string(self) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            serializer.data["book"]["daily_fee"],
            "2.30",
        )

    def test_actual_return_date_is_returned_as_null(self) -> None:
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertIsNone(
            serializer.data["actual_return_date"]
        )

    def test_serializer_fields_are_read_only(self) -> None:
        original_expected_return_date = (
            self.borrowing.expected_return_date
        )
        new_expected_return_date = (
            original_expected_return_date
            + timedelta(days=7)
        )

        serializer = BorrowingReadSerializer(
            instance=self.borrowing,
            data={
                "borrow_date": "2026-01-01",
                "expected_return_date": (
                    new_expected_return_date.isoformat()
                ),
                "actual_return_date": "2026-01-10",
                "book": self.book.id,
                "user": self.user.id,
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
