"""Dashboard numbers must come from the database and respect who is asking."""
import pytest

from tests.conftest import make_ticket

URL = "/api/dashboard/"


@pytest.mark.django_db
class TestDashboard:
    def test_requires_authentication(self, api):
        assert api.get(URL).status_code == 401

    def test_agent_statistics_are_exact(self, login, agent, customer, other_customer):
        make_ticket(customer, priority="high")
        make_ticket(customer, status="in_progress", assigned_to=agent, priority="low")
        make_ticket(other_customer, status="resolved", assigned_to=agent)
        make_ticket(other_customer, status="closed", priority="urgent")
        data = login(agent).get(URL).data
        assert data["scope"] == "all" and data["total"] == 4
        assert data["by_status"] == {"open": 1, "in_progress": 1, "resolved": 1, "closed": 1}
        assert data["by_priority"] == {"low": 1, "medium": 1, "high": 1, "urgent": 1}
        assert data["unassigned"] == 1  # the open one; the unassigned CLOSED ticket does not count
        assert data["assigned_to_me"] == 2
        assert data["created_last_7_days"] == 4

    def test_customer_only_sees_own_numbers_and_no_staff_fields(self, login, customer, other_customer):
        make_ticket(customer)
        make_ticket(other_customer)
        make_ticket(other_customer)
        data = login(customer).get(URL).data
        assert data["scope"] == "own" and data["total"] == 1
        assert data["unassigned"] is None and data["assigned_to_me"] is None

    def test_empty_database_returns_zeroes_not_errors(self, login, agent):
        data = login(agent).get(URL).data
        assert data["total"] == 0 and data["by_priority"] == {"low": 0, "medium": 0, "high": 0, "urgent": 0}
