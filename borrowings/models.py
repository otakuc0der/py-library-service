from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from books.models import Book
from borrowings.utils.validators import get_borrowing_date_errors


class Borrowing(models.Model):
    borrow_date = models.DateField(
        default=timezone.localdate,
        editable=False,
    )
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(
        null=True,
        blank=True,
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )

    class Meta:
        ordering = ["-borrow_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    expected_return_date__gte=F(
                        "borrow_date"
                    )
                ),
                name=(
                    "expected_return_not_before_borrow"
                ),
            ),
            models.CheckConstraint(
                condition=(
                    Q(actual_return_date__isnull=True)
                    | Q(
                        actual_return_date__gte=F(
                            "borrow_date"
                        )
                    )
                ),
                name=(
                    "actual_return_not_before_borrow"
                ),
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors = get_borrowing_date_errors(
            borrow_date=self.borrow_date,
            expected_return_date=self.expected_return_date,
            actual_return_date=self.actual_return_date,
        )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return (
            f"{self.user} borrowed "
            f"{self.book}"
        )
