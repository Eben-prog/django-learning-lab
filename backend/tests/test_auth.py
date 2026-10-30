"""Registration, login, token refresh, logout, profile. Why: if auth breaks, nothing else is reachable."""
import pytest
from django.conf import settings

from accounts.models import User
from tests.conftest import TEST_PASSWORD

REGISTER = {"username": "newbie", "email": "NewBie@Example.test", "password": "Str0ng-and-unusual-pw", "first_name": "New"}


@pytest.mark.django_db
class TestRegister:
    def test_creates_customer_and_hashes_password(self, api):
        response = api.post("/api/auth/register/", REGISTER, format="json")
        assert response.status_code == 201
        assert "password" not in response.data
        user = User.objects.get(username="newbie")
        assert user.role == "customer"
        assert user.email == "newbie@example.test"  # normalised to lowercase
        assert user.password != REGISTER["password"] and user.password.startswith("pbkdf2_")
        assert user.check_password(REGISTER["password"])

    def test_cannot_choose_own_role(self, api):
        api.post("/api/auth/register/", {**REGISTER, "role": "admin"}, format="json")
        assert User.objects.get(username="newbie").role == "customer"

    def test_duplicate_email_is_rejected_case_insensitively(self, api, customer):
        response = api.post("/api/auth/register/", {**REGISTER, "email": customer.email.upper()}, format="json")
        assert response.status_code == 400
        assert "email" in response.data["error"]["fields"]

    def test_weak_password_is_rejected(self, api):
        response = api.post("/api/auth/register/", {**REGISTER, "password": "12345678"}, format="json")
        assert response.status_code == 400
        assert "password" in response.data["error"]["fields"]


@pytest.mark.django_db
class TestLoginRefreshLogout:
    def test_login_returns_access_token_and_httponly_cookie(self, api, customer):
        response = api.post("/api/auth/login/", {"username": "cust", "password": TEST_PASSWORD}, format="json")
        assert response.status_code == 200
        assert response.data["access"] and response.data["user"]["role"] == "customer"
        cookie = response.cookies[settings.REFRESH_COOKIE_NAME]
        assert cookie["httponly"] and cookie["path"] == settings.REFRESH_COOKIE_PATH
        assert "refresh" not in response.data  # the refresh token is never exposed to JavaScript

    def test_wrong_password_gives_401_with_error_envelope(self, api, customer):
        response = api.post("/api/auth/login/", {"username": "cust", "password": "nope"}, format="json")
        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_failed"

    def test_inactive_user_cannot_log_in(self, api, customer):
        customer.is_active = False
        customer.save()
        response = api.post("/api/auth/login/", {"username": "cust", "password": TEST_PASSWORD}, format="json")
        assert response.status_code == 401

    def test_missing_fields_give_400(self, api):
        response = api.post("/api/auth/login/", {}, format="json")
        assert response.status_code == 400

    def test_access_token_authenticates_requests(self, api, customer):
        access = api.post("/api/auth/login/", {"username": "cust", "password": TEST_PASSWORD}, format="json").data["access"]
        response = api.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
        assert response.status_code == 200 and response.data["username"] == "cust"

    def test_garbage_token_gives_401(self, api):
        assert api.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer not-a-token").status_code == 401

    def test_refresh_uses_cookie_then_logout_clears_it(self, api, customer):
        api.post("/api/auth/login/", {"username": "cust", "password": TEST_PASSWORD}, format="json")
        refreshed = api.post("/api/auth/refresh/")  # the test client re-sends the cookie like a browser
        assert refreshed.status_code == 200 and refreshed.data["access"]
        assert api.post("/api/auth/logout/").status_code == 204
        assert api.post("/api/auth/refresh/").status_code == 401

    def test_refresh_without_cookie_is_401(self, api):
        assert api.post("/api/auth/refresh/").status_code == 401


@pytest.mark.django_db
class TestProfile:
    def test_requires_authentication(self, api):
        assert api.get("/api/auth/me/").status_code == 401

    def test_patch_updates_name_but_ignores_role(self, login, customer):
        response = login(customer).patch("/api/auth/me/", {"first_name": "Zed", "role": "admin"}, format="json")
        assert response.status_code == 200
        customer.refresh_from_db()
        assert customer.first_name == "Zed" and customer.role == "customer"

    def test_email_must_stay_unique(self, login, customer, other_customer):
        response = login(customer).patch("/api/auth/me/", {"email": other_customer.email}, format="json")
        assert response.status_code == 400

    def test_change_password(self, login, customer):
        client = login(customer)
        bad = client.post("/api/auth/change-password/", {"old_password": "wrong", "new_password": "An0ther-Strong-pw"}, format="json")
        assert bad.status_code == 400
        ok = client.post("/api/auth/change-password/", {"old_password": TEST_PASSWORD, "new_password": "An0ther-Strong-pw"}, format="json")
        assert ok.status_code == 204
        customer.refresh_from_db()
        assert customer.check_password("An0ther-Strong-pw")
