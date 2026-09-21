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


BORROWING_LIST_URL = reverse(
    "borrowings:borrowing-list"
)


class BorrowingFilterTestBase(APITestCase):
    @staticmethod
    def create_user(
        email: str,
        **extra_fields: Any,
    ) -> AbstractBaseUser:
        return get_user_model().objects.create_user(
            email=email,
            password="test-password",
            **extra_fields,
        )

    @staticmethod
    def create_book(
        title: str,
    ) -> Book:
        return Book.objects.create(
            title=title,
            author=f"{title} Author",
            cover=Book.Cover.HARD,
            inventory=10,
            daily_fee=Decimal("2.30"),
        )

    @staticmethod
    def create_borrowing(
        user: AbstractBaseUser,
        book: Book,
        actual_return_date=None,
    ) -> Borrowing:
        return Borrowing.objects.create(
            borrow_date=timezone.localdate(),
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
            actual_return_date=actual_return_date,
            user=user,
            book=book,
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

    @staticmethod
    def get_response_ids(response) -> set[int]:
        return {
            borrowing["id"]
            for borrowing in response.data
        }


class UnauthenticatedBorrowingFilterTests(
    BorrowingFilterTestBase,
):
    def test_unauthenticated_user_cannot_filter_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "is_active": "true",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class RegularUserBorrowingFilterTests(
    BorrowingFilterTestBase,
):
    def setUp(self) -> None:
        self.user = self.create_user(
            email="user@example.com",
        )
        self.other_user = self.create_user(
            email="other@example.com",
        )

        self.active_borrowing = (
            self.create_borrowing(
                user=self.user,
                book=self.create_book(
                    "Active User Book"
                ),
            )
        )
        self.returned_borrowing = (
            self.create_borrowing(
                user=self.user,
                book=self.create_book(
                    "Returned User Book"
                ),
                actual_return_date=(
                    timezone.localdate()
                ),
            )
        )
        self.other_active_borrowing = (
            self.create_borrowing(
                user=self.other_user,
                book=self.create_book(
                    "Other Active Book"
                ),
            )
        )
        self.other_returned_borrowing = (
            self.create_borrowing(
                user=self.other_user,
                book=self.create_book(
                    "Other Returned Book"
                ),
                actual_return_date=(
                    timezone.localdate()
                ),
            )
        )

        self.authenticate_user(self.user)

    def test_user_sees_only_own_borrowings_without_filters(
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
            self.get_response_ids(response),
            {
                self.active_borrowing.id,
                self.returned_borrowing.id,
            },
        )

    def test_user_can_filter_active_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "is_active": "true",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.get_response_ids(response),
            {
                self.active_borrowing.id,
            },
        )

    def test_user_can_filter_returned_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "is_active": "false",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.get_response_ids(response),
            {
                self.returned_borrowing.id,
            },
        )

    def test_user_id_filter_does_not_expose_other_user_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": self.other_user.id,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.get_response_ids(response),
            {
                self.active_borrowing.id,
                self.returned_borrowing.id,
            },
        )
        self.assertNotIn(
            self.other_active_borrowing.id,
            self.get_response_ids(response),
        )
        self.assertNotIn(
            self.other_returned_borrowing.id,
            self.get_response_ids(response),
        )

    def test_user_id_does_not_bypass_active_filter(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": self.other_user.id,
                "is_active": "true",
            },
        )

        self.assertEqual(
            self.get_response_ids(response),
            {
                self.active_borrowing.id,
            },
        )


class AdminBorrowingFilterTests(
    BorrowingFilterTestBase,
):
    def setUp(self) -> None:
        self.admin = self.create_user(
            email="admin@example.com",
            is_staff=True,
        )
        self.first_user = self.create_user(
            email="first@example.com",
        )
        self.second_user = self.create_user(
            email="second@example.com",
        )
        self.user_without_borrowings = (
            self.create_user(
                email="empty@example.com",
            )
        )

        self.first_active = (
            self.create_borrowing(
                user=self.first_user,
                book=self.create_book(
                    "First Active Book"
                ),
            )
        )
        self.first_returned = (
            self.create_borrowing(
                user=self.first_user,
                book=self.create_book(
                    "First Returned Book"
                ),
                actual_return_date=(
                    timezone.localdate()
                ),
            )
        )
        self.second_active = (
            self.create_borrowing(
                user=self.second_user,
                book=self.create_book(
                    "Second Active Book"
                ),
            )
        )
        self.second_returned = (
            self.create_borrowing(
                user=self.second_user,
                book=self.create_book(
                    "Second Returned Book"
                ),
                actual_return_date=(
                    timezone.localdate()
                ),
            )
        )

        self.authenticate_user(self.admin)

    def test_admin_sees_all_borrowings_without_filters(
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
            self.get_response_ids(response),
            {
                self.first_active.id,
                self.first_returned.id,
                self.second_active.id,
                self.second_returned.id,
            },
        )

    def test_admin_can_filter_by_user_id(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": self.first_user.id,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.get_response_ids(response),
            {
                self.first_active.id,
                self.first_returned.id,
            },
        )

    def test_admin_gets_empty_list_for_user_without_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": (
                    self.user_without_borrowings.id
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            [],
        )

    def test_admin_gets_empty_list_for_missing_user_id(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": 999_999,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            [],
        )

    def test_admin_can_filter_active_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "is_active": "true",
            },
        )

        self.assertEqual(
            self.get_response_ids(response),
            {
                self.first_active.id,
                self.second_active.id,
            },
        )

    def test_admin_can_filter_returned_borrowings(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "is_active": "false",
            },
        )

        self.assertEqual(
            self.get_response_ids(response),
            {
                self.first_returned.id,
                self.second_returned.id,
            },
        )

    def test_admin_can_combine_user_and_active_filters(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": self.first_user.id,
                "is_active": "true",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.get_response_ids(response),
            {
                self.first_active.id,
            },
        )

    def test_admin_can_combine_user_and_returned_filters(
        self,
    ) -> None:
        response = self.client.get(
            BORROWING_LIST_URL,
            {
                "user_id": self.second_user.id,
                "is_active": "false",
            },
        )

        self.assertEqual(
            self.get_response_ids(response),
            {
                self.second_returned.id,
            },
        )
