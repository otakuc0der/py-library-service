from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from borrowings.utils.validators import (
    get_borrowing_date_errors,
    validate_book_inventory,
)


class BorrowingReadSerializer(
    serializers.ModelSerializer,
):
    book = BookSerializer(
        read_only=True,
    )

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        )
        read_only_fields = fields


class BorrowingCreateSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "expected_return_date",
            "book",
        )
        read_only_fields = (
            "id",
        )

    def validate_expected_return_date(
        self,
        expected_return_date: date,
    ) -> date:
        errors = get_borrowing_date_errors(
            borrow_date=timezone.localdate(),
            expected_return_date=(
                expected_return_date
            ),
        )

        if errors:
            raise serializers.ValidationError(
                errors["expected_return_date"]
            )

        return expected_return_date

    def validate_book(
        self,
        book: Book,
    ) -> Book:
        error = validate_book_inventory(
            inventory=book.inventory
        )

        if error:
            raise serializers.ValidationError(error)

        return book

    def create(
        self,
        validated_data: dict[str, Any],
    ) -> Borrowing:
        selected_book = validated_data.pop(
            "book"
        )

        with transaction.atomic():
            locked_book = (
                Book.objects.select_for_update()
                .get(pk=selected_book.pk)
            )

            inventory_error = validate_book_inventory(
                inventory=locked_book.inventory
            )

            if inventory_error:
                raise serializers.ValidationError(
                    {
                        "book": inventory_error,
                    }
                )

            borrowing = Borrowing.objects.create(
                book=locked_book,
                **validated_data,
            )

            locked_book.inventory -= 1
            locked_book.save(
                update_fields=["inventory"],
            )

            return borrowing
