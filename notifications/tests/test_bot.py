from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from books.models import Book
from borrowings.models import Borrowing
from notifications.bot import (
    format_fine_payment_completed_message,
    format_payment_completed_message,
    format_payment_notification_message,
    send_overdue_borrowings_report,
    send_telegram_message,
)
from payments.models import Payment


class PaymentNotificationFormattingTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="test-password",
        )

        self.book = Book.objects.create(
            title="Test Title",
            author="Test Author",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("1.50"),
        )

        self.borrowing = Borrowing.objects.create(
            borrow_date=date(2026, 9, 5),
            expected_return_date=date(2026, 9, 10),
            actual_return_date=date(2026, 9, 15),
            book=self.book,
            user=self.user,
        )

        self.regular_payment = Payment.objects.create(
            status=Payment.Status.PAID,
            type=Payment.Type.PAYMENT,
            borrowing=self.borrowing,
            session_url="https://checkout.stripe.com/regular",
            session_id="cs_test_regular",
            money_to_pay=Decimal("7.50"),
        )

        self.fine_payment = Payment.objects.create(
            status=Payment.Status.PAID,
            type=Payment.Type.FINE,
            borrowing=self.borrowing,
            session_url="https://checkout.stripe.com/fine",
            session_id="cs_test_fine",
            money_to_pay=Decimal("15.00"),
        )

    def test_format_payment_completed_message_contains_payment_details(
        self,
    ) -> None:
        regular_payment_msg = format_payment_completed_message(
            payment=self.regular_payment
        )

        with self.subTest("test appropriate text header presence"):
            self.assertIn("Borrowing Payment Received", regular_payment_msg)

        with self.subTest("test appropriate user email presence"):
            self.assertIn(self.user.email, regular_payment_msg)

        with self.subTest("test appropriate book title presence"):
            self.assertIn(self.book.title, regular_payment_msg)

        with self.subTest("test appropriate payment money to pay presence"):
            self.assertIn(
                f"Amount: ${self.regular_payment.money_to_pay:.2f}",
                regular_payment_msg,
            )

        with self.subTest("test appropriate payment id presence"):
            self.assertIn(
                f"Payment ID: {self.regular_payment.id}",
                regular_payment_msg,
            )

        with self.subTest("test appropriate borrowing id presence"):
            self.assertIn(
                f"Borrowing ID: {self.borrowing.id}",
                regular_payment_msg,
            )

        with self.subTest("test appropriate status (paid) presence"):
            self.assertIn("Status: ✅ Paid", regular_payment_msg)

    def test_format_fine_payment_completed_message_contains_fine_details(
        self,
    ) -> None:
        fine_payment_msg = format_fine_payment_completed_message(
            payment=self.fine_payment
        )

        with self.subTest("test appropriate text header presence"):
            self.assertIn("Overdue Fine Payment Received", fine_payment_msg)

        result_expected_return_date = self.borrowing.expected_return_date.strftime(
            "%B %d, %Y"
        )

        with self.subTest("test appropriate expected return date presence"):
            self.assertIn(result_expected_return_date, fine_payment_msg)

        result_actual_return_date = self.borrowing.actual_return_date.strftime(
            "%B %d, %Y"
        )

        with self.subTest("test appropriate actual return date presence"):
            self.assertIn(result_actual_return_date, fine_payment_msg)

        overdue_days = (
            self.borrowing.actual_return_date
            - self.borrowing.expected_return_date
        ).days

        with self.subTest("test appropriate overdue amount presence"):
            self.assertIn(f"Overdue by: {overdue_days} days", fine_payment_msg)

        with self.subTest("test appropriate fine money to pay presence"):
            self.assertIn(
                f"Amount: ${self.fine_payment.money_to_pay:.2f}",
                fine_payment_msg,
            )

        with self.subTest("test appropriate type presence"):
            self.assertIn("Type: Overdue fine", fine_payment_msg)

        with self.subTest("test appropriate status presence"):
            self.assertIn("Status: ✅ Paid", fine_payment_msg)

    def test_format_fine_payment_message_uses_singular_day(
        self,
    ) -> None:
        self.borrowing.actual_return_date = date(2026, 9, 11)
        fine_payment_msg = format_fine_payment_completed_message(
            payment=self.fine_payment
        )
        self.assertIn("Overdue by: 1 day", fine_payment_msg)
        self.assertNotIn("1 days", fine_payment_msg)

    def test_format_fine_payment_message_raises_error_for_active_borrowing(
        self,
    ) -> None:
        self.borrowing.actual_return_date = None

        with self.assertRaisesMessage(
            ValueError,
            "A fine payment requires a returned borrowing.",
        ):
            format_fine_payment_completed_message(
                payment=self.fine_payment
            )

    @patch("notifications.bot.format_payment_completed_message")
    def test_payment_notification_uses_regular_formatter_for_payment(
        self,
        mocked_formatter: MagicMock,
    ) -> None:
        mocked_formatter.return_value = "regular payment message"

        message = format_payment_notification_message(
            self.regular_payment
        )

        self.assertEqual(mocked_formatter.return_value, message)

        mocked_formatter.assert_called_once_with(self.regular_payment)

    @patch("notifications.bot.format_fine_payment_completed_message")
    def test_payment_notification_uses_fine_formatter_for_fine(
        self,
        mocked_formatter: MagicMock,
    ) -> None:
        mocked_formatter.return_value = "fine payment message"

        message = format_payment_notification_message(
            self.fine_payment
        )

        self.assertEqual(mocked_formatter.return_value, message)

        mocked_formatter.assert_called_once_with(self.fine_payment)

    def test_payment_message_escapes_html_in_dynamic_values(
        self,
    ) -> None:
        self.book.title = "Clean <Code> & Python"
        self.book.save(update_fields=["title"])
        msg = format_payment_completed_message(self.regular_payment)
        self.assertIn(
            "Title: Clean &lt;Code&gt; &amp; Python",
            msg,
        )


class TelegramMessageSendingTests(SimpleTestCase):
    @override_settings(
        TELEGRAM_BOT_TOKEN="test-token",
        TELEGRAM_CHAT_ID=123456,
    )
    @patch("notifications.bot.Bot")
    async def test_send_telegram_message_uses_configured_bot_and_chat(
        self,
        mocked_bot_class: MagicMock,
    ) -> None:
        fake_bot = mocked_bot_class.return_value
        fake_bot.send_message = AsyncMock()

        await send_telegram_message("Test notification")

        mocked_bot_class.assert_called_once_with(token="test-token")
        fake_bot.send_message.assert_awaited_once_with(
            chat_id=123456,
            text="Test notification",
            parse_mode="HTML",
        )


class OverdueBorrowingsReportTests(SimpleTestCase):
    @patch(
        "notifications.bot.send_telegram_message",
        new_callable=AsyncMock,
    )
    @patch("notifications.bot.format_no_overdue_borrowings_message")
    async def test_report_sends_no_overdue_message_for_empty_list(
        self,
        mocked_formatter: MagicMock,
        mocked_send_message: AsyncMock,
    ) -> None:
        mocked_formatter.return_value = "No overdue borrowings"

        await send_overdue_borrowings_report([])

        mocked_formatter.assert_called_once_with()
        mocked_send_message.assert_awaited_once_with(
            "No overdue borrowings"
        )

    async def test_report_sends_started_borrowing_and_completed_messages(
        self,
    ) -> None:
        borrowing = MagicMock(spec=Borrowing)

        with (
            patch(
                "notifications.bot.format_overdue_report_started_message",
                return_value="Report started",
            ) as mocked_started_formatter,
            patch(
                "notifications.bot.format_overdue_borrowing_message",
                return_value="Borrowing overdue",
            ) as mocked_borrowing_formatter,
            patch(
                "notifications.bot.format_overdue_report_completed_message",
                return_value="Report completed",
            ) as mocked_completed_formatter,
            patch(
                "notifications.bot.send_telegram_message",
                new_callable=AsyncMock,
            ) as mocked_send_message,
        ):
            await send_overdue_borrowings_report([borrowing])

            mocked_started_formatter.assert_called_once_with(1)
            mocked_borrowing_formatter.assert_called_once_with(borrowing)
            mocked_completed_formatter.assert_called_once_with(1)

            mocked_send_message.assert_has_awaits(
                [
                    call(mocked_started_formatter.return_value),
                    call(mocked_borrowing_formatter.return_value),
                    call(mocked_completed_formatter.return_value)
                ]
            )

            self.assertEqual(mocked_send_message.await_count, 3)

    async def test_report_sends_message_for_each_overdue_borrowing(
        self,
    ) -> None:
        first_borrowing = MagicMock(spec=Borrowing)
        second_borrowing = MagicMock(spec=Borrowing)

        with (
            patch(
                "notifications.bot.format_overdue_report_started_message",
                return_value="Report started",
            ) as mocked_started_formatter,
            patch(
                "notifications.bot.format_overdue_borrowing_message",
                side_effect=[
                    "First overdue borrowing",
                    "Second overdue borrowing",
                ]
            ) as mocked_borrowing_formatter,
            patch(
                "notifications.bot.format_overdue_report_completed_message",
                return_value="Report completed",
            ) as mocked_completed_formatter,
            patch(
                "notifications.bot.send_telegram_message",
                new_callable=AsyncMock,
            ) as mocked_send_message,
        ):
            await send_overdue_borrowings_report(
                [first_borrowing, second_borrowing]
            )

            mocked_started_formatter.assert_called_once_with(2)
            self.assertEqual(
                mocked_borrowing_formatter.call_args_list,
                [
                    call(first_borrowing),
                    call(second_borrowing),
                ],
            )
            mocked_completed_formatter.assert_called_once_with(2)

            mocked_send_message.assert_has_awaits(
                [
                    call("Report started"),
                    call("First overdue borrowing"),
                    call("Second overdue borrowing"),
                    call("Report completed"),
                ]
            )

            self.assertEqual(mocked_send_message.await_count, 4)
