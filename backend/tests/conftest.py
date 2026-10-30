"""
Shared fixtures (pytest's version of JUnit @BeforeEach setup / Spring test config).
A fixture is a function whose RETURN VALUE is injected into any test that names it as a parameter.
Each test runs inside a database transaction that is rolled back afterwards, so tests don't leak data.
"""
import pytest
from rest_framework.test import APIClient

from accounts.models import User
from tickets.models import Ticket

TEST_PASSWORD = "Test-only-Passw0rd!"  # used only against the throw-away test database


def make_user(username: str, role: str, **extra) -> User:
    return User.objects.create_user(username=username, email=f"{username}@example.test", password=TEST_PASSWORD, role=role, **extra)


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def customer(db):
    return make_user("cust", "customer")


@pytest.fixture
def other_customer(db):
    return make_user("cust2", "customer")


@pytest.fixture
def agent(db):
    return make_user("agent", "agent")


@pytest.fixture
def other_agent(db):
    return make_user("agent2", "agent")


@pytest.fixture
def admin_user(db):
    return make_user("boss", "admin", is_staff=True)


@pytest.fixture
def login(api):
    """login(user) -> the same client, now authenticated as that user (skips the JWT round trip)."""

    def _login(user):
        api.force_authenticate(user=user)
        return api

    return _login


@pytest.fixture
def ticket(customer):
    return Ticket.objects.create(
        title="Printer is on fire", description="Smoke is coming out of the office printer.", created_by=customer, updated_by=customer
    )


def make_ticket(creator, **kwargs) -> Ticket:
    defaults = {"title": "Some problem here", "description": "A long enough description.", "updated_by": creator}
    return Ticket.objects.create(created_by=creator, **{**defaults, **kwargs})
