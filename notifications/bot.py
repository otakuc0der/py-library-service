from html import escape

from django.conf import settings
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


async def send_telegram_message(message: str) -> None:
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
    )

    await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
    )
