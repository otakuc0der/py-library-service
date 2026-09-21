from datetime import timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Book
from borrowings.models import Borrowing


def get_borrowing_return_url(borrowing_id: int) -> str:
    return reverse(
        "borrowings:borrowing-return",
        args=[borrowing_id],
    )


class BorrowingReturnTestBase(APITestCase):
    @staticmethod
    def create_user(
        email: str,
        password: str = "test-password",
        **extra_fields: Any,
    ) -> AbstractBaseUser:
        return get_user_model().objects.create_user(
            email=email,
            password=password,
            **extra_fields,
        )

    @staticmethod
    def create_book(
        title: str = "The Little Prince",
        author: str = "Antoine de Saint-Exupéry",
        inventory: int = 4,
    ) -> Book:
        return Book.objects.create(
            title=title,
            author=author,
            cover=Book.Cover.HARD,
            inventory=inventory,
            daily_fee=Decimal("2.30"),
        )

    @staticmethod
    def create_borrowing(
        user: AbstractBaseUser,
        book: Book,
        **changes: Any,
    ) -> Borrowing:
        borrowing_data = {
            "borrow_date": timezone.localdate(),
            "expected_return_date": (
                    timezone.localdate()
                    + timedelta(days=7)
            ),
            "actual_return_date": None,
            "user": user,
            "book": book,
        }
        borrowing_data.update(changes)

        return Borrowing.objects.create(
            **borrowing_data
        )

    def authenticate_user(
        self,
        user: AbstractBaseUser,
    ) -> None:
        access_token = RefreshToken.for_user(
            user
        ).access_token

        self.client.credentials(
            HTTP_AUTHORIZE=(
                f"Bearer {access_token}"
            )
        )


class UnauthenticatedBorrowingReturnTests(BorrowingReturnTestBase):
    def setUp(self) -> None:
        self.user = self.create_user(
            email="user@example.com",
        )
        self.book = self.create_book()
        self.borrowing = self.create_borrowing(
            user=self.user,
            book=self.book,
        )

    def test_unauthenticated_user_cannot_return_borrowing(
        self
    ) -> None:
        original_inventory = self.book.inventory

        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertIsNone(
            self.borrowing.actual_return_date
        )
        self.assertEqual(
            self.book.inventory,
            original_inventory,
        )


class AuthenticatedBorrowingReturnTests(BorrowingReturnTestBase):
    def setUp(self) -> None:
        self.user = self.create_user(
            email="user@example.com",
        )
        self.other_user = self.create_user(
            email="other@example.com",
        )

        self.book = self.create_book()
        self.other_book = self.create_book(
            title="Clean Code",
            author="Robert C. Martin",
            inventory=7,
        )

        self.borrowing = self.create_borrowing(
            user=self.user,
            book=self.book,
        )
        self.other_borrowing = (
            self.create_borrowing(
                user=self.other_user,
                book=self.other_book,
            )
        )

        self.authenticate_user(self.user)

    def test_user_can_return_own_borrowing(self) -> None:
        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_return_sets_actual_return_date(self) -> None:
        self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.borrowing.refresh_from_db()

        self.assertEqual(
            self.borrowing.actual_return_date,
            timezone.localdate(),
        )

    def test_return_increases_book_inventory(self) -> None:
        original_inventory = self.book.inventory

        self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.inventory,
            original_inventory + 1,
        )

    def test_return_response_contains_return_date(
        self
    ) -> None:
        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.data["actual_return_date"],
            timezone.localdate().isoformat(),
        )

    def test_return_response_contains_updated_inventory(
        self
    ) -> None:
        original_inventory = self.book.inventory

        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.data["book"]["inventory"],
            original_inventory + 1,
        )

    def test_return_response_uses_detail_representation(
        self
    ) -> None:
        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            set(response.data["book"]),
            {
                "id",
                "title",
                "author",
                "cover",
                "inventory",
                "daily_fee",
            },
        )
        self.assertEqual(
            response.data["user"],
            {
                "id": self.user.id,
                "email": self.user.email,
            },
        )

    def test_return_does_not_require_request_body(
        self
    ) -> None:
        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_borrowing_cannot_be_returned_twice(self) -> None:
        return_url = get_borrowing_return_url(
            self.borrowing.id
        )

        first_response = self.client.post(
            return_url,
            data={},
            format="json",
        )
        second_response = self.client.post(
            return_url,
            data={},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "actual_return_date",
            second_response.data,
        )
        self.assertEqual(
            second_response.data["actual_return_date"],
            "This borrowing has already been returned.",
        )

    def test_repeated_return_does_not_increase_inventory_twice(
        self
    ) -> None:
        original_inventory = self.book.inventory
        return_url = get_borrowing_return_url(
            self.borrowing.id
        )

        self.client.post(
            return_url,
            data={},
            format="json",
        )
        self.client.post(
            return_url,
            data={},
            format="json",
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.inventory,
            original_inventory + 1,
        )

    def test_user_cannot_return_other_user_borrowing(
        self
    ) -> None:
        original_inventory = (
            self.other_book.inventory
        )

        response = self.client.post(
            get_borrowing_return_url(
                self.other_borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.other_borrowing.refresh_from_db()
        self.other_book.refresh_from_db()

        self.assertIsNone(
            self.other_borrowing.actual_return_date
        )
        self.assertEqual(
            self.other_book.inventory,
            original_inventory,
        )

    def test_missing_borrowing_returns_not_found(
        self
    ) -> None:
        response = self.client.post(
            get_borrowing_return_url(999_999),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_get_method_is_not_allowed(self) -> None:
        response = self.client.get(
            get_borrowing_return_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_transaction_rolls_back_when_book_update_fails(
        self
    ) -> None:
        original_inventory = self.book.inventory

        with patch.object(
            Book,
            "save",
            side_effect=RuntimeError(
                "Book update failed."
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    get_borrowing_return_url(
                        self.borrowing.id
                    ),
                    data={},
                    format="json",
                )

        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertIsNone(
            self.borrowing.actual_return_date
        )
        self.assertEqual(
            self.book.inventory,
            original_inventory,
        )


class AdminBorrowingReturnTests(BorrowingReturnTestBase):
    def setUp(self) -> None:
        self.admin = self.create_user(
            email="admin@example.com",
            is_staff=True,
        )
        self.user = self.create_user(
            email="user@example.com",
        )
        self.book = self.create_book()
        self.borrowing = self.create_borrowing(
            user=self.user,
            book=self.book,
        )

        self.authenticate_user(self.admin)

    def test_admin_can_return_any_borrowing(self) -> None:
        original_inventory = self.book.inventory

        response = self.client.post(
            get_borrowing_return_url(
                self.borrowing.id
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertEqual(
            self.borrowing.actual_return_date,
            timezone.localdate(),
        )
        self.assertEqual(
            self.book.inventory,
            original_inventory + 1,
        )

    def test_admin_cannot_return_borrowing_twice(
        self
    ) -> None:
        return_url = get_borrowing_return_url(
            self.borrowing.id
        )

        self.client.post(
            return_url,
            data={},
            format="json",
        )
        response = self.client.post(
            return_url,
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_missing_borrowing_returns_not_found(
        self
    ) -> None:
        response = self.client.post(
            get_borrowing_return_url(999_999),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
