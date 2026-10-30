"""Authorization matrix: who may call what. Hiding a React button is not security; these tests are."""
import pytest

from accounts.models import User


@pytest.mark.django_db
class TestAnonymous:
    @pytest.mark.parametrize(
        "method,url",
        [
            ("get", "/api/tickets/"),
            ("post", "/api/tickets/"),
            ("get", "/api/tickets/1/"),
            ("get", "/api/dashboard/"),
            ("get", "/api/users/"),
            ("get", "/api/auth/me/"),
        ],
    )
    def test_protected_endpoints_return_401(self, api, method, url):
        assert getattr(api, method)(url).status_code == 401

    def test_health_is_public_and_checks_database(self, api):
        response = api.get("/api/health/")
        assert response.status_code == 200 and response.data["database"] == "ok"


@pytest.mark.django_db
class TestUserManagement:
    def test_customer_cannot_list_users(self, login, customer):
        assert login(customer).get("/api/users/").status_code == 403

    def test_agent_can_list_agents_for_the_assignment_dropdown(self, login, agent, customer):
        response = login(agent).get("/api/users/", {"role": "agent"})
        assert response.status_code == 200
        assert {u["username"] for u in response.data["results"]} == {"agent"}

    def test_agent_cannot_change_roles(self, login, agent, customer):
        assert login(agent).patch(f"/api/users/{customer.id}/", {"role": "admin"}, format="json").status_code == 403

    def test_admin_can_promote_a_customer_to_agent(self, login, admin_user, customer):
        response = login(admin_user).patch(f"/api/users/{customer.id}/", {"role": "agent"}, format="json")
        assert response.status_code == 200
        customer.refresh_from_db()
        assert customer.role == "agent"

    def test_admin_cannot_demote_or_deactivate_self(self, login, admin_user):
        client = login(admin_user)
        assert client.patch(f"/api/users/{admin_user.id}/", {"role": "customer"}, format="json").status_code == 400
        assert client.patch(f"/api/users/{admin_user.id}/", {"is_active": False}, format="json").status_code == 400

    def test_invalid_role_is_400(self, login, admin_user, customer):
        assert login(admin_user).patch(f"/api/users/{customer.id}/", {"role": "superhero"}, format="json").status_code == 400

    def test_put_is_not_allowed_on_user_detail(self, login, admin_user, customer):
        assert login(admin_user).put(f"/api/users/{customer.id}/", {"role": "agent"}, format="json").status_code == 405

    def test_deactivated_user_loses_api_access(self, api, customer):
        from rest_framework_simplejwt.tokens import AccessToken

        token = str(AccessToken.for_user(customer))
        assert api.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 200
        User.objects.filter(pk=customer.pk).update(is_active=False)
        assert api.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 401
