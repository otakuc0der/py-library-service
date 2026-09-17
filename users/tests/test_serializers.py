from django.contrib.auth import get_user_model
from django.test import TestCase

from users.serializers import UserSerializer


class UserSerializerTests(TestCase):
    def test_create_user(self) -> None:
        serializer = UserSerializer(
            data={
                "email": "user@example.com",
                "password": "test-password",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        user = serializer.save()

        self.assertEqual(
            user.email,
            "user@example.com",
        )
        self.assertTrue(
            user.check_password("test-password")
        )

    def test_password_is_not_returned(self) -> None:
        serializer = UserSerializer(
            data={
                "email": "user@example.com",
                "password": "test-password",
            }
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        response_data = UserSerializer(user).data

        self.assertNotIn(
            "password",
            response_data,
        )

    def test_short_password_is_invalid(self) -> None:
        serializer = UserSerializer(
            data={
                "email": "user@example.com",
                "password": "1234",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "password",
            serializer.errors,
        )

    def test_duplicate_email_is_invalid(self) -> None:
        get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )

        serializer = UserSerializer(
            data={
                "email": "user@example.com",
                "password": "other-password",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "email",
            serializer.errors,
        )

    def test_update_user_email(self) -> None:
        user = get_user_model().objects.create_user(
            email="old@example.com",
            password="test-password",
        )

        serializer = UserSerializer(
            instance=user,
            data={
                "email": "new@example.com",
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        self.assertEqual(
            updated_user.email,
            "new@example.com",
        )

    def test_update_user_password(self) -> None:
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="old-password",
        )

        serializer = UserSerializer(
            instance=user,
            data={
                "password": "new-password",
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        self.assertFalse(
            updated_user.check_password("old-password")
        )
        self.assertTrue(
            updated_user.check_password("new-password")
        )
