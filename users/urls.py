from django.urls import path

from users.views import (
    CreateUserView,
    ManageUserView,
    MyTokenObtainPairView,
    MyTokenRefreshView,
)


app_name = "users"

urlpatterns = [
    path(
        "",
        CreateUserView.as_view(),
        name="create",
    ),
    path(
        "token/",
        MyTokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),
    path(
        "token/refresh/",
        MyTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "me/",
        ManageUserView.as_view(),
        name="manage",
    ),
]
