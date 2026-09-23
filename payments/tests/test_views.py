from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


class PaymentViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test-password",
        )
        cls.another_user = (
            get_user_model().objects.create_user(
                email="another@example.com",
                password="test-password",
            )
        )
        cls.admin = (
            get_user_model().objects.create_superuser(
                email="admin@example.com",
                password="admin-password",
            )
        )

        cls.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            cover="soft",
            inventory=10,
            daily_fee=Decimal("2.50"),
        )

        cls.user_borrowing = Borrowing.objects.create(
            user=cls.user,
            book=cls.book,
            expected_return_date=(
                timezone.localdate()
                + timedelta(days=7)
            ),
        )
        cls.another_user_borrowing = (
            Borrowing.objects.create(
                user=cls.another_user,
                book=cls.book,
                expected_return_date=(
                    timezone.localdate()
                    + timedelta(days=10)
                ),
            )
        )

        cls.user_payment = Payment.objects.create(
            borrowing=cls.user_borrowing,
            status=Payment.Status.PENDING,
            type=Payment.Type.PAYMENT,
            session_url=(
                "https://checkout.stripe.com/"
                "user-session"
            ),
            session_id="cs_test_user",
            money_to_pay=Decimal("12.50"),
        )
        cls.another_user_payment = (
            Payment.objects.create(
                borrowing=(
                    cls.another_user_borrowing
                ),
                status=Payment.Status.PAID,
                type=Payment.Type.FINE,
                session_url=(
                    "https://checkout.stripe.com/"
                    "another-session"
                ),
                session_id="cs_test_another",
                money_to_pay=Decimal("25.00"),
            )
        )

        cls.list_url = reverse(
            "payments:payment-list",
        )

    def test_unauthenticated_user_cannot_list_payments(
        self,
    ) -> None:
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_retrieve_payment(
        self,
    ) -> None:
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_regular_user_sees_only_own_payments(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            payment["id"]
            for payment in response.data
        }

        self.assertEqual(
            returned_ids,
            {self.user_payment.id},
        )

    def test_regular_user_can_retrieve_own_payment(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.user_payment.id,
        )

    def test_regular_user_cannot_retrieve_another_users_payment(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.another_user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_sees_all_payments(self) -> None:
        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            payment["id"]
            for payment in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                self.user_payment.id,
                self.another_user_payment.id,
            },
        )

    def test_admin_can_retrieve_any_payment(self) -> None:
        self.client.force_authenticate(
            user=self.admin,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.another_user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.another_user_payment.id,
        )

    def test_payment_response_contains_expected_fields(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        response = self.client.get(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            set(response.data),
            {
                "id",
                "status",
                "type",
                "borrowing",
                "session_url",
                "session_id",
                "money_to_pay",
            },
        )

    def test_payment_endpoints_do_not_allow_write_methods(
        self,
    ) -> None:
        self.client.force_authenticate(
            user=self.user,
        )
        detail_url = reverse(
            "payments:payment-detail",
            args=[self.user_payment.id],
        )

        requests = [
            (
                self.client.post,
                self.list_url,
            ),
            (
                self.client.put,
                detail_url,
            ),
            (
                self.client.patch,
                detail_url,
            ),
            (
                self.client.delete,
                detail_url,
            ),
        ]

        for request_method, url in requests:
            with self.subTest(method=request_method.__name__):
                response = request_method(
                    url,
                    data={},
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
