from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "hard", "Hard"
        SOFT = "soft", "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(
        max_length=5,
        choices=Cover.choices,
        default=Cover.HARD,
    )
    inventory = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
    )
    daily_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["title", "author"]
        constraints = [
            models.CheckConstraint(
                condition=Q(daily_fee__gte=0),
                name="daily_fee_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(inventory__gte=0),
                name="inventory_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title}, {self.author}"
