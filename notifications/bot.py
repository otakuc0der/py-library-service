from html import escape

from django.conf import settings
from django.utils import timezone
from telegram import Bot

from borrowings.models import Borrowing


def format_new_borrowing_message(borrowing: Borrowing) -> str:
    return (
        "📚 <b>New Borrowing Created</b>\n\n"
        "👤 <b>Borrower</b>\n"
        f"Email: {escape(borrowing.user.email)}\n"
        f"User ID: {borrowing.user_id}\n\n"
        "📖 <b>Book</b>\n"
        f"Title: {escape(borrowing.book.title)}\n"
        f"Author: {escape(borrowing.book.author)}\n"
        f"Book ID: {borrowing.book_id}\n\n"
        "📅 <b>Borrowing Details</b>\n"
        f"Borrowing ID: {borrowing.id}\n"
        f"Borrowed on: "
        f"{borrowing.borrow_date:%B %d, %Y}\n"
        f"Expected return: "
        f"{borrowing.expected_return_date:%B %d, %Y}\n\n"
        "📦 <b>Available copies remaining:</b> "
        f"{borrowing.book.inventory}"
    )


def format_overdue_report_started_message(borrowings_count: int) -> str:
    today = timezone.localdate()

    borrowing_word = (
        "borrowing"
        if borrowings_count == 1
        else "borrowings"
    )

    return (
        "🚨 <b>Daily Overdue Borrowings "
        "Report</b>\n\n"
        f"📅 Date: {today:%B %d, %Y}\n"
        f"📊 Found: {borrowings_count} overdue "
        f"{borrowing_word}\n\n"
        "Detailed notifications for each overdue "
        "borrowing will follow."
    )


def format_overdue_borrowing_message(borrowing: Borrowing) -> str:
    today = timezone.localdate()
    overdue_days = (
        today - borrowing.expected_return_date
    ).days

    if overdue_days == 0:
        title = "⚠️ <b>Borrowing Due Today</b>"
        due_information = (
            "⏳ <b>Due:</b> Today"
        )
    else:
        title = "🚨 <b>Borrowing Overdue</b>"
        day_word = (
            "day"
            if overdue_days == 1
            else "days"
        )
        due_information = (
            f"⏳ <b>Overdue by:</b> "
            f"{overdue_days} {day_word}"
        )

    return (
        f"{title}\n\n"
        "👤 <b>Borrower</b>\n"
        f"Email: {escape(borrowing.user.email)}\n"
        f"User ID: {borrowing.user_id}\n\n"
        "📖 <b>Book</b>\n"
        f"Title: {escape(borrowing.book.title)}\n"
        f"Author: {escape(borrowing.book.author)}\n"
        f"Book ID: {borrowing.book_id}\n\n"
        "📅 <b>Borrowing Details</b>\n"
        f"Borrowing ID: {borrowing.id}\n"
        f"Borrowed on: "
        f"{borrowing.borrow_date:%B %d, %Y}\n"
        f"Expected return: "
        f"{borrowing.expected_return_date:%B %d, %Y}\n"
        f"{due_information}\n\n"
        "🔴 <b>Status:</b> Not returned"
    )


def format_overdue_report_completed_message(
    borrowings_count: int,
) -> str:
    borrowing_word = (
        "borrowing"
        if borrowings_count == 1
        else "borrowings"
    )

    return (
        "📋 <b>Overdue Borrowings Report "
        "Completed</b>\n\n"
        f"✅ Processed: {borrowings_count} overdue "
        f"{borrowing_word}\n\n"
        "All overdue borrowing details have been "
        "published.\n"
        "Administrator attention is required."
    )


def format_no_overdue_borrowings_message() -> str:
    today = timezone.localdate()

    return (
        "✅ <b>No Borrowings Overdue Today</b>\n\n"
        f"📅 Date: {today:%B %d, %Y}\n\n"
        "All borrowed books are currently within "
        "their expected return periods or have "
        "already been returned."
    )


async def send_telegram_message(message: str) -> None:
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
    )

    await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
    )


async def send_overdue_borrowings_report(
    borrowings: list[Borrowing],
) -> None:
    if not borrowings:
        message = (
            format_no_overdue_borrowings_message()
        )
        await send_telegram_message(message)
        return

    started_message = (
        format_overdue_report_started_message(
            len(borrowings)
        )
    )
    await send_telegram_message(
        started_message
    )

    for borrowing in borrowings:
        borrowing_message = (
            format_overdue_borrowing_message(
                borrowing
            )
        )
        await send_telegram_message(
            borrowing_message
        )

    completed_message = (
        format_overdue_report_completed_message(
            len(borrowings)
        )
    )
    await send_telegram_message(
        completed_message
    )
