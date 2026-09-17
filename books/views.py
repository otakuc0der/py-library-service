from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from books.models import Book
from books.permissions import IsAdminOrReadOnly
from books.serializers import BookSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List books",
        description=(
            "Return all books available in the library inventory. "
            "Authentication is not required."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve a book",
        description=(
            "Return information about one book by its ID. "
            "Authentication is not required."
        ),
    ),
    create=extend_schema(
        summary="Create a book",
        description=(
            "Create a new book in the library inventory. "
            "Only administrators can perform this operation."
        ),
    ),
    update=extend_schema(
        summary="Update a book",
        description=(
            "Replace all editable fields of an existing book. "
            "Only administrators can perform this operation."
        ),
    ),
    partial_update=extend_schema(
        summary="Partially update a book",
        description=(
            "Update one or more fields of an existing book. "
            "Only administrators can perform this operation."
        ),
    ),
    destroy=extend_schema(
        summary="Delete a book",
        description=(
            "Remove a book from the library inventory. "
            "Only administrators can perform this operation."
        ),
    ),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnly]
