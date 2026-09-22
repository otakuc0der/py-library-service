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
from borrowings.serializers import (
    BorrowingDetailSerializer,
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
        inventory: int = 12,
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
        data = {
            "borrow_date": timezone.localdate(),
            "expected_return_date": (
                timezone.localdate()
                + timedelta(days=7)
            ),
            "actual_return_date": None,
            "user": user,
            "book": book,
        }
        data.update(changes)

        return Borrowing.objects.create(**data)

    @staticmethod
    def get_create_data(
        selected_book: Book,
        **changes: Any,
    ) -> dict:
        data = {
            "expected_return_date": (
                timezone.localdate()
                + timedelta(days=7)
            ).isoformat(),
            "book": selected_book.id,
        }
        data.update(changes)

        return data

    def authenticate_user(
        self,
        user: AbstractBaseUser,
    ) -> None:
        token = RefreshToken.for_user(
            user
        ).access_token

        self.client.credentials(
            HTTP_AUTHORIZE=f"Bearer {token}"
        )


class UnauthenticatedBorrowingViewTests(
    BorrowingViewTestBase
):
    def setUp(self) -> None:
        self.user = self.create_user(
            "user@example.com"
        )
        self.book = self.create_book()
        self.borrowing = self.create_borrowing(
            self.user,
            self.book,
        )

    def test_cannot_get_list(self) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_cannot_get_detail(self) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_cannot_create_borrowing(self) -> None:
        response = self.client.post(
            BORROWING_LIST_URL,
            data=self.get_create_data(
                self.book
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class AuthenticatedBorrowingViewTests(
    BorrowingViewTestBase
):
    def setUp(self) -> None:
        self.user = self.create_user(
            "user@example.com"
        )
        self.other_user = self.create_user(
            "other@example.com"
        )
        self.book = self.create_book()
        self.other_book = self.create_book(
            title="Clean Code",
            author="Robert C. Martin",
        )

        self.borrowing = self.create_borrowing(
            self.user,
            self.book,
        )
        self.other_borrowing = (
            self.create_borrowing(
                self.other_user,
                self.other_book,
            )
        )

        self.authenticate_user(self.user)

    def test_list_returns_brief_book_and_user(
        self
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            set(response.data[0]["book"]),
            {
                "id",
                "title",
                "author",
            },
        )
        self.assertEqual(
            set(response.data[0]["user"]),
            {
                "id",
                "email",
            },
        )

    def test_user_sees_only_own_borrowings(
        self
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            self.borrowing.id,
        )

    def test_user_can_retrieve_own_borrowing(
        self
    ) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )
        expected_data = (
            BorrowingDetailSerializer(
                self.borrowing
            ).data
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            expected_data,
        )

    def test_detail_returns_full_book(self) -> None:
        response = self.client.get(
            get_borrowing_detail_url(
                self.borrowing.id
            )
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

    def test_user_cannot_retrieve_other_borrowing(
        self
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

    @patch(
        "borrowings.views.send_new_borrowing_notification.delay"
    )
    def test_user_can_create_borrowing(
        self,
        mock_send_new_borrowing_notification_delay,
    ) -> None:
        initial_count = Borrowing.objects.count()

        response = self.client.post(
            BORROWING_LIST_URL,
            data=self.get_create_data(
                self.book
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            Borrowing.objects.count(),
            initial_count + 1,
        )

        borrowing = Borrowing.objects.get(
            id=response.data["id"]
        )
        self.assertEqual(
            borrowing.user,
            self.user,
        )

    @patch(
        "borrowings.views.send_new_borrowing_notification.delay"
    )
    def test_create_returns_detail_representation(
        self,
        mock_send_new_borrowing_notification_delay,
    ) -> None:
        response = self.client.post(
            BORROWING_LIST_URL,
            data=self.get_create_data(
                self.book
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
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

    def test_update_is_not_allowed(self) -> None:
        response = self.client.put(
            get_borrowing_detail_url(
                self.borrowing.id
            ),
            data=self.get_create_data(
                self.book
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_partial_update_is_not_allowed(self) -> None:
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

    def test_delete_is_not_allowed(self) -> None:
        response = self.client.delete(
            get_borrowing_detail_url(
                self.borrowing.id
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class AdminBorrowingViewTests(
    BorrowingViewTestBase
):
    def setUp(self) -> None:
        self.admin = self.create_user(
            "admin@example.com",
            is_staff=True,
        )
        self.user = self.create_user(
            "user@example.com"
        )
        self.book = self.create_book()
        self.borrowing = self.create_borrowing(
            self.user,
            self.book,
        )

        self.authenticate_user(self.admin)

    def test_admin_sees_all_borrowings(
        self
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data[0]["id"],
            self.borrowing.id,
        )

    def test_admin_can_retrieve_any_borrowing(
        self
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
