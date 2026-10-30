"""
Auth flow:
  login   -> returns {"access": <15 min JWT>, "user": {...}} and sets an HttpOnly `refresh_token` cookie
  refresh -> reads the cookie, returns a new access token
  logout  -> deletes the cookie
React keeps the access token in memory only (see frontend/src/api/client.ts).
"""
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.permissions import IsAdminRole, IsSupportStaff
from accounts.serializers import (
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from config.exceptions import error_body


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,  # invisible to JavaScript
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def _unauthorized(message: str) -> Response:
    return Response(error_body(401, "authentication_failed", message), status=status.HTTP_401_UNAUTHORIZED)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # a stale/expired token must not break sign-up
    queryset = User.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # authenticate() verifies the password hash and rejects inactive users.
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            # Same message for "unknown user" and "wrong password" so attackers can't enumerate usernames.
            return _unauthorized("Invalid username or password.")
        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)
        response = Response({"access": str(refresh.access_token), "user": UserSerializer(user).data})
        _set_refresh_cookie(response, str(refresh))
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw_token:
            return _unauthorized("No refresh token. Please log in.")
        try:
            refresh = RefreshToken(raw_token)  # verifies signature and expiry
        except TokenError:
            response = _unauthorized("Session expired. Please log in again.")
            _clear_refresh_cookie(response)
            return response
        user = User.objects.filter(pk=refresh["user_id"], is_active=True).first()
        if user is None:
            return _unauthorized("Account not found or disabled.")
        return Response({"access": str(refresh.access_token), "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH the current user's own profile."""

    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserListView(generics.ListAPIView):
    """Support staff can list users (the assignment dropdown needs agents)."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSupportStaff]
    queryset = User.objects.order_by("username")
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]


class UserDetailView(generics.RetrieveUpdateAPIView):
    """Admins can read a user and change role / active flag."""

    permission_classes = [IsAuthenticated, IsAdminRole]
    queryset = User.objects.all()
    http_method_names = ["get", "patch", "head", "options"]  # no PUT: only partial updates make sense here

    def get_serializer_class(self):
        return AdminUserUpdateSerializer if self.request.method == "PATCH" else UserSerializer

    def update(self, request, *args, **kwargs):
        serializer = AdminUserUpdateSerializer(self.get_object(), data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)
