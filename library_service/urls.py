from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/books/",
        include(
            "books.urls",
            namespace="books",
        ),
    ),
    path(
        "api/users/",
        include(
            "users.urls",
            namespace="users",
        ),
    ),
    path(
        "api/borrowings/",
        include(
            "borrowings.urls",
            namespace="borrowings",
        ),
    ),
    path(
        "api/payments/",
        include(
            "payments.urls",
            namespace="payments",
        ),
    ),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
        ),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
