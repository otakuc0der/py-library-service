from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from books.models import Book


class BookModelTests(TestCase):
    @staticmethod
    def get_book_data(**changes) -> dict:
        book_data = {
            "title": "The Little Prince",
            "author": "Antoine de Saint-Exupéry",
            "cover": Book.Cover.HARD,
            "inventory": 12,
            "daily_fee": Decimal("2.30"),
        }
        book_data.update(changes)

        return book_data

    def test_create_book_with_correct_data(self) -> None:
        book_data = self.get_book_data()

        book = Book.objects.create(**book_data)

        self.assertIsInstance(book.id, int)
        self.assertGreater(book.id, 0)
        self.assertEqual(book.title, book_data["title"])
        self.assertEqual(book.author, book_data["author"])
        self.assertEqual(book.cover, book_data["cover"])
        self.assertEqual(
            book.inventory,
            book_data["inventory"],
        )
        self.assertEqual(
            book.daily_fee,
            book_data["daily_fee"],
        )

    def test_str_returns_title_and_author(self) -> None:
        book = Book.objects.create(
            **self.get_book_data()
        )

        self.assertEqual(
            str(book),
            "The Little Prince, Antoine de Saint-Exupéry",
        )

    def test_inventory_can_equal_zero(self) -> None:
        book = Book.objects.create(
            **self.get_book_data(inventory=0)
        )

        self.assertEqual(book.inventory, 0)

    def test_daily_fee_can_equal_zero(self) -> None:
        book = Book.objects.create(
            **self.get_book_data(
                daily_fee=Decimal("0.00"),
            )
        )

        self.assertEqual(
            book.daily_fee,
            Decimal("0.00"),
        )

    def test_negative_daily_fee_fails_validation(
        self,
    ) -> None:
        book = Book(
            **self.get_book_data(
                daily_fee=Decimal("-1.00"),
            )
        )

        with self.assertRaises(ValidationError) as error:
            book.full_clean()

        self.assertIn(
            "daily_fee",
            error.exception.message_dict,
        )

    def test_negative_inventory_fails_validation(
        self,
    ) -> None:
        book = Book(
            **self.get_book_data(inventory=-1)
        )

        with self.assertRaises(ValidationError) as error:
            book.full_clean()

        self.assertIn(
            "inventory",
            error.exception.message_dict,
        )

    def test_negative_daily_fee_fails_database_constraint(
        self,
    ) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Book.objects.create(
                    **self.get_book_data(
                        daily_fee=Decimal("-1.00"),
                    )
                )

    def test_negative_inventory_fails_database_constraint(
        self,
    ) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Book.objects.create(
                    **self.get_book_data(
                        inventory=-1,
                    )
                )

    def test_invalid_cover_fails_validation(self) -> None:
        book = Book(
            **self.get_book_data(cover="invalid")
        )

        with self.assertRaises(ValidationError) as error:
            book.full_clean()

        self.assertIn(
            "cover",
            error.exception.message_dict,
        )

    def test_hard_cover_passes_validation(self) -> None:
        book = Book(
            **self.get_book_data(
                cover=Book.Cover.HARD,
            )
        )

        book.full_clean()

    def test_soft_cover_passes_validation(self) -> None:
        book = Book(
            **self.get_book_data(
                cover=Book.Cover.SOFT,
            )
        )

        book.full_clean()

    def test_books_are_ordered_by_title_and_author(
        self,
    ) -> None:
        second_book = Book.objects.create(
            **self.get_book_data(
                title="Clean Code",
                author="Robert C. Martin",
            )
        )
        first_book = Book.objects.create(
            **self.get_book_data(
                title="A Game of Thrones",
                author="George R. R. Martin",
            )
        )

        self.assertQuerySetEqual(
            Book.objects.all(),
            [first_book, second_book],
        )
