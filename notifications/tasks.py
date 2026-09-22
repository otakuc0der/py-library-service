from asgiref.sync import async_to_sync
from celery import shared_task

from borrowings.models import Borrowing
from borrowings.utils.helpers import (
    get_overdue_borrowings,
)
from notifications.bot import (
    format_new_borrowing_message,
    send_overdue_borrowings_report,
    send_telegram_message,
)


@shared_task
def send_new_borrowing_notification(
    borrowing_id: int,
) -> None:
    borrowing = (
        Borrowing.objects
        .select_related(
            "book",
            "user",
        )
        .get(id=borrowing_id)
    )

    message = format_new_borrowing_message(
        borrowing
    )

    async_to_sync(
        send_telegram_message
    )(message)


@shared_task
def check_overdue_borrowings() -> None:
    overdue_borrowings = list(
        get_overdue_borrowings()
    )

    async_to_sync(
        send_overdue_borrowings_report
    )(overdue_borrowings)
