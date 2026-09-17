from decimal import Decimal
from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Book


BOOK_LIST_URL = reverse("books:book-list")


def get_book_detail_url(book_id: UUID) -> str:
    return reverse(
        "books:book-detail",
        args=[book_id],
    )


class BookPermissionTestBase(APITestCase):
    @staticmethod
    def get_book_data(**changes: Any) -> dict:
        book_data = {
            "title": "The Little Prince",
            "author": "Antoine de Saint-Exupéry",
            "cover": Book.Cover.HARD,
            "inventory": 12,
            "daily_fee": Decimal("2.30"),
        }
        book_data.update(changes)

        return book_data

    def create_book(self, **changes: Any) -> Book:
        return Book.objects.create(
            **self.get_book_data(**changes)
        )

    @staticmethod
    def create_user(
        email: str = "user@example.com",
        password: str = "test-password",
        **extra_fields: Any,
    ) -> AbstractBaseUser:
        return get_user_model().objects.create_user(
            email=email,
            password=password,
            **extra_fields,
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


class UnauthenticatedBookPermissionTests(
    BookPermissionTestBase,
):
    def setUp(self) -> None:
        self.book = self.create_book()

    def test_can_list_books(self) -> None:
        response = self.client.get(
            BOOK_LIST_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_can_retrieve_book(self) -> None:
        response = self.client.get(
            get_book_detail_url(self.book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_cannot_create_book(self) -> None:
        response = self.client.post(
            BOOK_LIST_URL,
            data=self.get_book_data(
                title="New Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            Book.objects.count(),
            1,
        )

    def test_cannot_update_book(self) -> None:
        response = self.client.put(
            get_book_detail_url(self.book.id),
            data=self.get_book_data(
                title="Updated Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.title,
            "The Little Prince",
        )

    def test_cannot_partially_update_book(
        self,
    ) -> None:
        response = self.client.patch(
            get_book_detail_url(self.book.id),
            data={
                "inventory": 20,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.inventory,
            12,
        )

    def test_cannot_delete_book(self) -> None:
        response = self.client.delete(
            get_book_detail_url(self.book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertTrue(
            Book.objects.filter(
                id=self.book.id,
            ).exists()
        )

    def test_default_authorization_header_is_not_accepted(
        self,
    ) -> None:
        admin_user = self.create_user(
            email="admin@example.com",
            password="admin-password",
            is_staff=True,
        )
        access_token = RefreshToken.for_user(
            admin_user
        ).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {access_token}"
            )
        )

        response = self.client.post(
            BOOK_LIST_URL,
            data=self.get_book_data(
                title="New Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            Book.objects.count(),
            1,
        )


class AuthenticatedUserBookPermissionTests(
    BookPermissionTestBase,
):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.book = self.create_book()

        self.authenticate_user(
            self.user,
        )

    def test_can_list_books(self) -> None:
        response = self.client.get(
            BOOK_LIST_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_can_retrieve_book(self) -> None:
        response = self.client.get(
            get_book_detail_url(self.book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_cannot_create_book(self) -> None:
        response = self.client.post(
            BOOK_LIST_URL,
            data=self.get_book_data(
                title="New Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            Book.objects.count(),
            1,
        )

    def test_cannot_update_book(self) -> None:
        response = self.client.put(
            get_book_detail_url(self.book.id),
            data=self.get_book_data(
                title="Updated Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.title,
            "The Little Prince",
        )

    def test_cannot_partially_update_book(
        self,
    ) -> None:
        response = self.client.patch(
            get_book_detail_url(self.book.id),
            data={
                "inventory": 20,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.inventory,
            12,
        )

    def test_cannot_delete_book(self) -> None:
        response = self.client.delete(
            get_book_detail_url(self.book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            Book.objects.filter(
                id=self.book.id,
            ).exists()
        )


class AdminBookPermissionTests(
    BookPermissionTestBase,
):
    def setUp(self) -> None:
        self.admin_user = self.create_user(
            email="admin@example.com",
            password="admin-password",
            is_staff=True,
        )
        self.book = self.create_book()

        self.authenticate_user(
            self.admin_user,
        )

    def test_can_list_books(self) -> None:
        response = self.client.get(
            BOOK_LIST_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_can_retrieve_book(self) -> None:
        response = self.client.get(
            get_book_detail_url(self.book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_can_create_book(self) -> None:
        response = self.client.post(
            BOOK_LIST_URL,
            data=self.get_book_data(
                title="New Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            Book.objects.count(),
            2,
        )
        self.assertTrue(
            Book.objects.filter(
                title="New Book",
            ).exists()
        )

    def test_can_update_book(self) -> None:
        response = self.client.put(
            get_book_detail_url(self.book.id),
            data=self.get_book_data(
                title="Updated Book",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.title,
            "Updated Book",
        )

    def test_can_partially_update_book(
        self,
    ) -> None:
        response = self.client.patch(
            get_book_detail_url(self.book.id),
            data={
                "inventory": 20,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.book.refresh_from_db()

        self.assertEqual(
            self.book.inventory,
            20,
        )

    def test_can_delete_book(self) -> None:
        response = self.client.delete(
            get_book_detail_url(self.book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Book.objects.filter(
                id=self.book.id,
            ).exists()
        )
