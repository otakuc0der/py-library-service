from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.models import User
from users.serializers import UserSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        summary="Obtain JWT tokens",
        description=(
            "Authenticate a user with an email and password. "
            "Return JWT access and refresh tokens."
        ),
    ),
)
class MyTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        summary="Refresh JWT access token",
        description=(
            "Accept a valid refresh token and return a new "
            "JWT access token."
        ),
    ),
)
class MyTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


@extend_schema_view(
    post=extend_schema(
        tags=["Users"],
        summary="Register a user",
        description=(
            "Create a new user account with an email and password. "
            "The password is stored as a secure hash and is never "
            "returned in the response."
        ),
        responses={
            201: UserSerializer,
            400: OpenApiResponse(
                description="Invalid registration data.",
            ),
        },
    ),
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        summary="Retrieve current user",
        description=(
            "Return the profile of the authenticated user."
        ),
        responses={
            200: UserSerializer,
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not provided "
                    "or the access token is invalid."
                ),
            ),
        },
    ),
    put=extend_schema(
        tags=["Users"],
        summary="Update current user",
        description=(
            "Replace the editable data of the authenticated user. "
            "A new password is securely hashed before it is saved."
        ),
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Invalid user data.",
            ),
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not provided "
                    "or the access token is invalid."
                ),
            ),
        },
    ),
    patch=extend_schema(
        tags=["Users"],
        summary="Partially update current user",
        description=(
            "Update one or more fields of the authenticated user. "
            "A new password is securely hashed before it is saved."
        ),
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Invalid user data.",
            ),
            401: OpenApiResponse(
                description=(
                    "Authentication credentials were not provided "
                    "or the access token is invalid."
                ),
            ),
        },
    ),
)
class ManageUserView(
    generics.RetrieveUpdateAPIView,
):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user
