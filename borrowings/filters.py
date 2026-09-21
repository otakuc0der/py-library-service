from django.db.models import QuerySet
from django_filters import rest_framework as filters

from borrowings.models import Borrowing


class BorrowingFilter(filters.FilterSet):
    user_id = filters.NumberFilter(
        method="filter_by_user_id",
        label="User ID",
        help_text=(
            "Filter borrowings by user ID. "
            "Available only to admins."
        ),
    )
    is_active = filters.BooleanFilter(
        method="filter_by_is_active",
        label="Is active",
        help_text=(
            "Filter active or returned borrowings. "
            "An active borrowing has no actual return date."
        ),
    )

    class Meta:
        model = Borrowing
        fields = []

    def filter_by_user_id(
        self,
        queryset: QuerySet[Borrowing],
        name: str,
        value: int,
    ) -> QuerySet[Borrowing]:
        if self.request.user.is_staff:
            return queryset.filter(
                user_id=value
            )

        return queryset

    def filter_by_is_active(
        self,
        queryset: QuerySet[Borrowing],
        name: str,
        value: bool | None,
    ) -> QuerySet[Borrowing]:
        if value is None:
            return queryset

        return queryset.filter(
            actual_return_date__isnull=value
        )
