from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingReadSerializer,
)


BORROWING_LIST_URL = reverse(
    "borrowings:borrowing-list"
)


def get_borrowing_detail_url(borrowing_id: int) -> str:
    return reverse(
        "borrowings:borrowing-detail",
        args=[borrowing_id],
    )


class BorrowingViewTestBase(APITestCase):
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
    ) -> Book:
        return Book.objects.create(
            title=title,
            author=author,
            cover=Book.Cover.HARD,
            inventory=12,
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


class UnauthenticatedBorrowingViewTests(
    BorrowingViewTestBase,
):
    def setUp(self) -> None:
        self.user = self.create_user(
            email="user@example.com",
        )
        self.book = self.create_book()
        self.borrowing = self.create_borrowing(
            user=self.user,
            book=self.book,
        )

    def test_cannot_get_borrowing_list(self) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_cannot_get_borrowing_detail(self) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class AuthenticatedUserBorrowingViewTests(BorrowingViewTestBase):
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

    def test_user_sees_own_borrowings(self) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            self.borrowing.id,
        )

    def test_user_does_not_see_other_user_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        borrowing_ids = [
            borrowing["id"]
            for borrowing in response.data
        ]

        self.assertNotIn(
            self.other_borrowing.id,
            borrowing_ids,
        )

    def test_user_can_retrieve_own_borrowing(
        self,
    ) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )
        serializer = BorrowingReadSerializer(
            self.borrowing
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            serializer.data,
        )

    def test_user_cannot_retrieve_other_user_borrowing(
        self,
    ) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.other_borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_missing_borrowing_returns_not_found(
        self,
    ) -> None:
        missing_id = (
            Borrowing
            .objects
            .order_by("-id")
            .first()
            .id
            + 1
        )

        response = self.client.get(
            get_borrowing_detail_url(
                missing_id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_borrowing_response_contains_nested_book(
        self,
    ) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIsInstance(
            response.data["book"],
            dict,
        )
        self.assertEqual(
            response.data["book"]["id"],
            self.book.id,
        )
        self.assertEqual(
            response.data["book"]["title"],
            self.book.title,
        )

    def test_user_cannot_create_borrowing(
        self,
    ) -> None:
        response = self.client.post(
            BORROWING_LIST_URL,
            data={
                "expected_return_date": (
                    timezone.localdate()
                    + timedelta(days=7)
                ).isoformat(),
                "book": self.book.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            Borrowing.objects.count(),
            2,
        )

    def test_user_cannot_update_borrowing(
        self,
    ) -> None:
        original_expected_return_date = (
            self.borrowing.expected_return_date
        )

        response = self.client.put(
            get_borrowing_detail_url(
                self.borrowing.id
            ),
            data={
                "expected_return_date": (
                    timezone.localdate()
                    + timedelta(days=14)
                ).isoformat(),
                "book": self.book.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.borrowing.refresh_from_db()

        self.assertEqual(
            self.borrowing.expected_return_date,
            original_expected_return_date,
        )

    def test_user_cannot_partially_update_borrowing(
        self,
    ) -> None:
        response = self.client.patch(
            get_borrowing_detail_url(
                self.borrowing.id
            ),
            data={
                "actual_return_date": (
                    timezone.localdate().isoformat()
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.borrowing.refresh_from_db()

        self.assertIsNone(
            self.borrowing.actual_return_date
        )

    def test_user_cannot_delete_borrowing(
        self,
    ) -> None:
        response = self.client.delete(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertTrue(
            Borrowing.objects.filter(
                id=self.borrowing.id,
            ).exists()
        )


class AdminBorrowingViewTests(
    BorrowingViewTestBase,
):
    def setUp(self) -> None:
        self.admin_user = self.create_user(
            email="admin@example.com",
            is_staff=True,
        )
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
        )

        self.first_borrowing = (
            self.create_borrowing(
                user=self.user,
                book=self.book,
            )
        )
        self.second_borrowing = (
            self.create_borrowing(
                user=self.other_user,
                book=self.other_book,
            )
        )

        self.authenticate_user(
            self.admin_user
        )

    def test_admin_sees_all_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            2,
        )

        borrowing_ids = {
            borrowing["id"]
            for borrowing in response.data
        }

        self.assertEqual(
            borrowing_ids,
            {
                self.first_borrowing.id,
                self.second_borrowing.id,
            },
        )

    def test_admin_can_retrieve_any_borrowing(
        self,
    ) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.second_borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.second_borrowing.id,
        )

    def test_admin_cannot_create_borrowing(
        self,
    ) -> None:
        response = self.client.post(
            BORROWING_LIST_URL,
            data={
                "expected_return_date": (
                    timezone.localdate()
                    + timedelta(days=7)
                ).isoformat(),
                "book": self.book.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            Borrowing.objects.count(),
            2,
        )

    def test_admin_cannot_update_borrowing(
        self,
    ) -> None:
        original_expected_return_date = (
            self.first_borrowing
            .expected_return_date
        )

        response = self.client.put(
            get_borrowing_detail_url(
                self.first_borrowing.id
            ),
            data={
                "expected_return_date": (
                    timezone.localdate()
                    + timedelta(days=14)
                ).isoformat(),
                "book": self.book.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.first_borrowing.refresh_from_db()

        self.assertEqual(
            self.first_borrowing
            .expected_return_date,
            original_expected_return_date,
        )

    def test_admin_cannot_partially_update_borrowing(self) -> None:
        response = self.client.patch(
            get_borrowing_detail_url(
                self.first_borrowing.id
            ),
            data={
                "actual_return_date": (
                    timezone.localdate().isoformat()
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.first_borrowing.refresh_from_db()

        self.assertIsNone(
            self.first_borrowing.actual_return_date
        )

    def test_admin_cannot_delete_borrowing(self) -> None:
        response = self.client.delete(
            get_borrowing_detail_url(
                self.first_borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertTrue(
            Borrowing.objects.filter(
                id=self.first_borrowing.id,
            ).exists()
        )
