from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from books.models import Book
from borrowings.models import Borrowing
from notifications.bot import (
    send_overdue_borrowings_report,
    send_telegram_message,
)
from notifications.tasks import (
    check_overdue_borrowings,
    send_new_borrowing_notification,
    send_payment_completed_notification,
)
from payments.models import Payment


class NotificationTasksTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="test-password",
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("2.00"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=date(2026, 9, 10),
            expected_return_date=date(2026, 9, 20),
            actual_return_date=None,
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            status=Payment.Status.PAID,
            type=Payment.Type.PAYMENT,
            session_url=(
                "https://checkout.stripe.com/"
                "test-payment"
            ),
            session_id="cs_test_payment",
            money_to_pay=Decimal("20.00"),
        )

    @patch("notifications.tasks.async_to_sync")
    @patch(
        "notifications.tasks."
        "format_new_borrowing_message"
    )
    def test_send_new_borrowing_notification_formats_and_sends_message(
        self,
        mocked_formatter: MagicMock,
        mocked_async_to_sync: MagicMock,
    ) -> None:
        mocked_formatter.return_value = (
            "New borrowing message"
        )

        mocked_sync_sender = MagicMock()
        mocked_async_to_sync.return_value = (
            mocked_sync_sender
        )

        send_new_borrowing_notification.run(
            self.borrowing.id
        )

        mocked_formatter.assert_called_once()

        formatted_borrowing = (
            mocked_formatter.call_args.args[0]
        )

        self.assertEqual(
            formatted_borrowing.id,
            self.borrowing.id,
        )

        mocked_async_to_sync.assert_called_once_with(
            send_telegram_message
        )
        mocked_sync_sender.assert_called_once_with(
            "New borrowing message"
        )

    @patch("notifications.tasks.async_to_sync")
    @patch(
        "notifications.tasks."
        "format_payment_notification_message"
    )
    def test_send_payment_completed_notification_formats_and_sends_message(
        self,
        mocked_formatter: MagicMock,
        mocked_async_to_sync: MagicMock,
    ) -> None:
        mocked_formatter.return_value = (
            "Payment completed message"
        )

        mocked_sync_sender = MagicMock()
        mocked_async_to_sync.return_value = (
            mocked_sync_sender
        )

        send_payment_completed_notification.run(
            self.payment.id
        )

        mocked_formatter.assert_called_once()

        formatted_payment = (
            mocked_formatter.call_args.args[0]
        )

        self.assertEqual(
            formatted_payment.id,
            self.payment.id,
        )

        mocked_async_to_sync.assert_called_once_with(
            send_telegram_message
        )
        mocked_sync_sender.assert_called_once_with(
            "Payment completed message"
        )

    @patch("notifications.tasks.async_to_sync")
    @patch(
        "notifications.tasks.get_overdue_borrowings"
    )
    def test_check_overdue_borrowings_sends_returned_queryset_as_list(
        self,
        mocked_get_overdue: MagicMock,
        mocked_async_to_sync: MagicMock,
    ) -> None:
        mocked_get_overdue.return_value = (
            Borrowing.objects.filter(
                id=self.borrowing.id,
            )
        )

        mocked_sync_report_sender = MagicMock()
        mocked_async_to_sync.return_value = (
            mocked_sync_report_sender
        )

        check_overdue_borrowings.run()

        mocked_get_overdue.assert_called_once_with()
        mocked_async_to_sync.assert_called_once_with(
            send_overdue_borrowings_report
        )

        mocked_sync_report_sender.assert_called_once()

        passed_borrowings = (
            mocked_sync_report_sender.call_args.args[0]
        )

        self.assertIsInstance(
            passed_borrowings,
            list,
        )
        self.assertEqual(
            [
                borrowing.id
                for borrowing in passed_borrowings
            ],
            [self.borrowing.id],
        )
