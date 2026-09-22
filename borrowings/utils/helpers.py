from django.db.models import QuerySet
from django.utils import timezone

from borrowings.models import Borrowing


def get_overdue_borrowings() -> QuerySet[Borrowing]:
    today = timezone.localdate()

    return (
        Borrowing
        .objects
        .select_related(
            "book",
            "user",
        )
        .filter(
            expected_return_date__lte=today,
            actual_return_date__isnull=True,
        )
        .order_by(
            "expected_return_date",
            "id",
        )
    )
