from django.contrib import admin

from borrowings.models import Borrowing


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "book",
        "user",
        "borrow_date",
        "expected_return_date",
        "actual_return_date",
    ]
    list_filter = [
        "borrow_date",
        "expected_return_date",
        "actual_return_date",
    ]
    search_fields = [
        "user__email",
        "book__title",
        "book__author",
    ]
    list_select_related = [
        "user",
        "book",
    ]
