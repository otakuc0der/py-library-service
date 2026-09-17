from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


class UserModelTests(TestCase):
    def test_create_user_with_email(self) -> None:
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )

        self.assertEqual(
            user.email,
            "user@example.com",
        )
        self.assertTrue(
            user.check_password("test-password")
        )

    def test_create_user_normalizes_email(self) -> None:
        user = get_user_model().objects.create_user(
            email="user@EXAMPLE.COM",
            password="test-password",
        )

        self.assertEqual(
            user.email,
            "user@example.com",
        )

    def test_create_user_without_email_raises_error(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                email="",
                password="test-password",
            )

    def test_create_regular_user_with_correct_flags(
        self,
    ) -> None:
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_with_correct_flags(
        self,
    ) -> None:
        user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="admin-password",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_without_staff_status_fails(
        self,
    ) -> None:
        with self.assertRaisesMessage(
            ValueError,
            "Superuser must have is_staff=True.",
        ):
            get_user_model().objects.create_superuser(
                email="admin@example.com",
                password="admin-password",
                is_staff=False,
            )

    def test_create_superuser_without_superuser_status_fails(
        self,
    ) -> None:
        with self.assertRaisesMessage(
            ValueError,
            "Superuser must have is_superuser=True.",
        ):
            get_user_model().objects.create_superuser(
                email="admin@example.com",
                password="admin-password",
                is_superuser=False,
            )

    def test_user_email_must_be_unique(self) -> None:
        get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                get_user_model().objects.create_user(
                    email="user@example.com",
                    password="other-password",
                )

    def test_user_string_representation(self) -> None:
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )

        self.assertEqual(
            str(user),
            "user@example.com",
        )
