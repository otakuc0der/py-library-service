from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Book
from books.serializers import BookSerializer


BOOK_LIST_URL = reverse("books:book-list")


def get_book_detail_url(book_id: int) -> str:
    return reverse(
        "books:book-detail",
        args=[book_id],
    )


class BookViewSetTests(APITestCase):
    def setUp(self) -> None:
        self.admin_user = (
            get_user_model().objects.create_user(
                email="admin@example.com",
                password="admin-password",
                is_staff=True,
            )
        )
        access_token = RefreshToken.for_user(
            self.admin_user
        ).access_token

        self.client.credentials(
            HTTP_AUTHORIZE=(
                f"Bearer {access_token}"
            )
        )

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

    def create_book(self, **changes) -> Book:
        return Book.objects.create(
            **self.get_book_data(**changes)
        )

    def test_get_empty_book_list(self) -> None:
        response = self.client.get(BOOK_LIST_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data, [])

    def test_get_book_list(self) -> None:
        self.create_book(
            title="Book A",
            author="Author A",
        )
        self.create_book(
            title="Book B",
            author="Author B",
        )

        response = self.client.get(BOOK_LIST_URL)

        books = Book.objects.all()
        serializer = BookSerializer(
            books,
            many=True,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            serializer.data,
        )

    def test_get_book_detail(self) -> None:
        book = self.create_book()
        serializer = BookSerializer(book)

        response = self.client.get(
            get_book_detail_url(book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            serializer.data,
        )

    def test_get_missing_book_returns_not_found(
        self,
    ) -> None:
        book = self.create_book()
        book_id = book.id
        book.delete()

        response = self.client.get(
            get_book_detail_url(book_id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_create_book(self) -> None:
        book_data = self.get_book_data(
            title="Clean Code",
            author="Robert C. Martin",
        )

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(Book.objects.count(), 1)

        book = Book.objects.get()

        self.assertEqual(
            book.title,
            book_data["title"],
        )
        self.assertEqual(
            book.author,
            book_data["author"],
        )
        self.assertEqual(
            book.cover,
            book_data["cover"],
        )
        self.assertEqual(
            book.inventory,
            book_data["inventory"],
        )
        self.assertEqual(
            book.daily_fee,
            book_data["daily_fee"],
        )

    def test_create_book_returns_created_book_data(
        self,
    ) -> None:
        book_data = self.get_book_data()

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        book = Book.objects.get()
        serializer = BookSerializer(book)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data,
            serializer.data,
        )

    def test_generated_id_cannot_be_overridden(
        self,
    ) -> None:
        requested_id = 999_999
        book_data = self.get_book_data(
            id=requested_id,
        )

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertNotEqual(
            response.data["id"],
            requested_id,
        )

    def test_create_book_without_title_returns_bad_request(
        self,
    ) -> None:
        book_data = self.get_book_data()
        book_data.pop("title")

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("title", response.data)
        self.assertFalse(Book.objects.exists())

    def test_create_book_with_invalid_cover_returns_bad_request(
        self,
    ) -> None:
        book_data = self.get_book_data(
            cover="invalid",
        )

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("cover", response.data)
        self.assertFalse(Book.objects.exists())

    def test_create_book_with_negative_inventory_returns_bad_request(
        self,
    ) -> None:
        book_data = self.get_book_data(
            inventory=-1,
        )

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("inventory", response.data)
        self.assertFalse(Book.objects.exists())

    def test_create_book_with_negative_daily_fee_returns_bad_request(
        self,
    ) -> None:
        book_data = self.get_book_data(
            daily_fee=Decimal("-1.00"),
        )

        response = self.client.post(
            BOOK_LIST_URL,
            data=book_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("daily_fee", response.data)
        self.assertFalse(Book.objects.exists())

    def test_update_book(self) -> None:
        book = self.create_book()

        updated_data = self.get_book_data(
            title="Updated Book",
            author="Updated Author",
            cover=Book.Cover.SOFT,
            inventory=5,
            daily_fee=Decimal("4.50"),
        )

        response = self.client.put(
            get_book_detail_url(book.id),
            data=updated_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        book.refresh_from_db()

        self.assertEqual(
            book.title,
            updated_data["title"],
        )
        self.assertEqual(
            book.author,
            updated_data["author"],
        )
        self.assertEqual(
            book.cover,
            updated_data["cover"],
        )
        self.assertEqual(
            book.inventory,
            updated_data["inventory"],
        )
        self.assertEqual(
            book.daily_fee,
            updated_data["daily_fee"],
        )

    def test_partially_update_book(self) -> None:
        book = self.create_book()
        original_title = book.title

        response = self.client.patch(
            get_book_detail_url(book.id),
            data={
                "inventory": 20,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        book.refresh_from_db()

        self.assertEqual(book.inventory, 20)
        self.assertEqual(
            book.title,
            original_title,
        )

    def test_update_book_with_invalid_data_returns_bad_request(
        self,
    ) -> None:
        book = self.create_book()
        original_daily_fee = book.daily_fee

        response = self.client.patch(
            get_book_detail_url(book.id),
            data={
                "daily_fee": Decimal("-3.00"),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        book.refresh_from_db()

        self.assertEqual(
            book.daily_fee,
            original_daily_fee,
        )

    def test_delete_book(self) -> None:
        book = self.create_book()

        response = self.client.delete(
            get_book_detail_url(book.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Book.objects.filter(
                id=book.id,
            ).exists()
        )

    def test_delete_missing_book_returns_not_found(
        self,
    ) -> None:
        book = self.create_book()
        book_id = book.id
        book.delete()

        response = self.client.delete(
            get_book_detail_url(book_id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
