from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import UserSerializer


CREATE_USER_URL = reverse("users:create")
TOKEN_URL = reverse("users:token-obtain-pair")
REFRESH_TOKEN_URL = reverse("users:token-refresh")
MANAGE_USER_URL = reverse("users:manage")


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


def get_access_token(
    user: AbstractBaseUser,
) -> str:
    refresh_token = RefreshToken.for_user(user)

    return str(refresh_token.access_token)


class PublicUserApiTests(APITestCase):
    def test_create_user(self) -> None:
        user_data = {
            "email": "user@example.com",
            "password": "test-password",
        }

        response = self.client.post(
            CREATE_USER_URL,
            data=user_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = get_user_model().objects.get(
            email=user_data["email"],
        )

        self.assertTrue(
            user.check_password(
                user_data["password"],
            )
        )
        self.assertNotIn(
            "password",
            response.data,
        )

    def test_create_user_returns_correct_data(
        self,
    ) -> None:
        user_data = {
            "email": "user@example.com",
            "password": "test-password",
        }

        response = self.client.post(
            CREATE_USER_URL,
            data=user_data,
            format="json",
        )

        user = get_user_model().objects.get(
            email=user_data["email"],
        )
        serializer = UserSerializer(user)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data,
            serializer.data,
        )

    def test_create_user_with_duplicate_email_fails(
        self,
    ) -> None:
        create_user(
            email="user@example.com",
        )

        response = self.client.post(
            CREATE_USER_URL,
            data={
                "email": "user@example.com",
                "password": "other-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )
        self.assertEqual(
            get_user_model().objects.count(),
            1,
        )

    def test_create_user_with_invalid_email_fails(
        self,
    ) -> None:
        response = self.client.post(
            CREATE_USER_URL,
            data={
                "email": "invalid-email",
                "password": "test-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )
        self.assertFalse(
            get_user_model().objects.exists()
        )

    def test_create_user_with_short_password_fails(
        self,
    ) -> None:
        response = self.client.post(
            CREATE_USER_URL,
            data={
                "email": "user@example.com",
                "password": "1234",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "password",
            response.data,
        )
        self.assertFalse(
            get_user_model().objects.exists()
        )

    def test_create_user_without_email_fails(
        self,
    ) -> None:
        response = self.client.post(
            CREATE_USER_URL,
            data={
                "password": "test-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )
        self.assertFalse(
            get_user_model().objects.exists()
        )

    def test_create_user_without_password_fails(
        self,
    ) -> None:
        response = self.client.post(
            CREATE_USER_URL,
            data={
                "email": "user@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "password",
            response.data,
        )
        self.assertFalse(
            get_user_model().objects.exists()
        )

    def test_create_user_cannot_set_staff_status(
        self,
    ) -> None:
        response = self.client.post(
            CREATE_USER_URL,
            data={
                "email": "user@example.com",
                "password": "test-password",
                "is_staff": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = get_user_model().objects.get(
            email="user@example.com",
        )

        self.assertFalse(user.is_staff)

    def test_create_token(self) -> None:
        create_user(
            email="user@example.com",
            password="test-password",
        )

        response = self.client.post(
            TOKEN_URL,
            data={
                "email": "user@example.com",
                "password": "test-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "access",
            response.data,
        )
        self.assertIn(
            "refresh",
            response.data,
        )

    def test_create_token_with_wrong_password_fails(
        self,
    ) -> None:
        create_user(
            email="user@example.com",
            password="correct-password",
        )

        response = self.client.post(
            TOKEN_URL,
            data={
                "email": "user@example.com",
                "password": "wrong-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertNotIn(
            "access",
            response.data,
        )
        self.assertNotIn(
            "refresh",
            response.data,
        )

    def test_create_token_for_unknown_user_fails(
        self,
    ) -> None:
        response = self.client.post(
            TOKEN_URL,
            data={
                "email": "unknown@example.com",
                "password": "test-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_create_token_without_credentials_fails(
        self,
    ) -> None:
        response = self.client.post(
            TOKEN_URL,
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )
        self.assertIn(
            "password",
            response.data,
        )

    def test_create_token_for_inactive_user_fails(
        self,
    ) -> None:
        create_user(
            email="inactive@example.com",
            password="test-password",
            is_active=False,
        )

        response = self.client.post(
            TOKEN_URL,
            data={
                "email": "inactive@example.com",
                "password": "test-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_access_token(self) -> None:
        user = create_user()
        refresh_token = RefreshToken.for_user(user)

        response = self.client.post(
            REFRESH_TOKEN_URL,
            data={
                "refresh": str(refresh_token),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "access",
            response.data,
        )

    def test_refresh_without_token_fails(self) -> None:
        response = self.client.post(
            REFRESH_TOKEN_URL,
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "refresh",
            response.data,
        )

    def test_refresh_with_invalid_token_fails(
        self,
    ) -> None:
        response = self.client.post(
            REFRESH_TOKEN_URL,
            data={
                "refresh": "invalid-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class UnauthenticatedManageUserApiTests(
    APITestCase,
):
    def setUp(self) -> None:
        self.user = create_user()

    def test_get_current_user_requires_authentication(
        self,
    ) -> None:
        response = self.client.get(
            MANAGE_USER_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_put_current_user_requires_authentication(
        self,
    ) -> None:
        response = self.client.put(
            MANAGE_USER_URL,
            data={
                "email": "updated@example.com",
                "password": "updated-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "user@example.com",
        )

    def test_patch_current_user_requires_authentication(
        self,
    ) -> None:
        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "email": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "user@example.com",
        )

    def test_default_authorization_header_is_not_accepted(
        self,
    ) -> None:
        access_token = get_access_token(
            self.user,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {access_token}"
            )
        )

        response = self.client.get(
            MANAGE_USER_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_authorize_token_is_rejected(
        self,
    ) -> None:
        self.client.credentials(
            HTTP_AUTHORIZE=(
                "Bearer invalid-token"
            )
        )

        response = self.client.get(
            MANAGE_USER_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authorize_header_without_bearer_is_rejected(
        self,
    ) -> None:
        access_token = get_access_token(
            self.user,
        )

        self.client.credentials(
            HTTP_AUTHORIZE=access_token,
        )

        response = self.client.get(
            MANAGE_USER_URL,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class AuthenticatedManageUserApiTests(
    APITestCase,
):
    def setUp(self) -> None:
        self.user = create_user()
        access_token = get_access_token(self.user)

        self.client.credentials(
            HTTP_AUTHORIZE=(
                f"Bearer {access_token}"
            )
        )

    def test_retrieve_current_user(self) -> None:
        response = self.client.get(MANAGE_USER_URL)
        serializer = UserSerializer(self.user)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            serializer.data,
        )
        self.assertNotIn(
            "password",
            response.data,
        )

    def test_retrieve_only_authenticated_user(
        self,
    ) -> None:
        other_user = create_user(
            email="other@example.com",
            password="other-password",
        )

        response = self.client.get(MANAGE_USER_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.user.id,
        )
        self.assertNotEqual(
            response.data["id"],
            other_user.id,
        )

    def test_partially_update_current_user(
        self,
    ) -> None:
        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "email": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "new@example.com",
        )

    def test_fully_update_current_user(
        self,
    ) -> None:
        response = self.client.put(
            MANAGE_USER_URL,
            data={
                "email": "updated@example.com",
                "password": "updated-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "updated@example.com",
        )
        self.assertTrue(
            self.user.check_password(
                "updated-password"
            )
        )

    def test_update_password(self) -> None:
        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "password": "new-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertNotIn(
            "password",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.check_password(
                "test-password"
            )
        )
        self.assertTrue(
            self.user.check_password(
                "new-password"
            )
        )

    def test_update_with_short_password_fails(
        self,
    ) -> None:
        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "password": "1234",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "password",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "test-password"
            )
        )

    def test_update_with_duplicate_email_fails(
        self,
    ) -> None:
        create_user(
            email="other@example.com",
        )

        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "email": "other@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "user@example.com",
        )

    def test_cannot_update_staff_status(
        self,
    ) -> None:
        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "is_staff": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_staff,
        )

    def test_update_does_not_change_other_user(
        self,
    ) -> None:
        other_user = create_user(
            email="other@example.com",
            password="other-password",
        )

        response = self.client.patch(
            MANAGE_USER_URL,
            data={
                "email": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()
        other_user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "updated@example.com",
        )
        self.assertEqual(
            other_user.email,
            "other@example.com",
        )
