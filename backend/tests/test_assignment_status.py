"""Assignment and status workflow, including the transactional guarantee of the service layer."""
from unittest import mock

import pytest
from rest_framework.exceptions import ValidationError

from tickets import services
from tickets.models import Comment, Ticket


def assign_url(t):
    return f"/api/tickets/{t.id}/assign/"


def status_url(t):
    return f"/api/tickets/{t.id}/status/"


@pytest.mark.django_db
class TestAssignment:
    def test_agent_assigns_ticket_and_it_starts_progress(self, login, agent, other_agent, ticket):
        response = login(agent).post(assign_url(ticket), {"assigned_to": other_agent.id}, format="json")
        assert response.status_code == 200
        ticket.refresh_from_db()
        assert ticket.assigned_to == other_agent and ticket.status == "in_progress" and ticket.updated_by == agent
        assert Comment.objects.filter(ticket=ticket, is_system=True, body__contains="agent2").exists()

    def test_customer_cannot_assign(self, login, customer, agent, ticket):
        assert login(customer).post(assign_url(ticket), {"assigned_to": agent.id}, format="json").status_code == 403

    def test_cannot_assign_to_a_customer(self, login, agent, other_customer, ticket):
        response = login(agent).post(assign_url(ticket), {"assigned_to": other_customer.id}, format="json")
        assert response.status_code == 400 and "assigned_to" in response.data["error"]["fields"]

    def test_cannot_assign_to_nonexistent_user(self, login, agent, ticket):
        assert login(agent).post(assign_url(ticket), {"assigned_to": 424242}, format="json").status_code == 400

    def test_null_unassigns(self, login, agent, ticket):
        ticket.assigned_to = agent
        ticket.save()
        assert login(agent).post(assign_url(ticket), {"assigned_to": None}, format="json").status_code == 200
        ticket.refresh_from_db()
        assert ticket.assigned_to is None

    def test_failure_midway_rolls_back_the_whole_operation(self, agent, ticket):
        """If writing the system comment fails, the ticket change must be undone too (transaction.atomic)."""
        with mock.patch("tickets.services.Comment.objects.create", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                services.assign_ticket(ticket, agent, agent)
        ticket.refresh_from_db()
        assert ticket.assigned_to is None and ticket.status == "open"


@pytest.mark.django_db
class TestStatus:
    def test_valid_transition_chain_sets_and_clears_closed_at(self, login, agent, ticket):
        client = login(agent)
        for new in ("in_progress", "resolved", "closed"):
            assert client.post(status_url(ticket), {"status": new}, format="json").status_code == 200
        ticket.refresh_from_db()
        assert ticket.status == "closed" and ticket.closed_at is not None
        assert client.post(status_url(ticket), {"status": "open"}, format="json").status_code == 200
        ticket.refresh_from_db()
        assert ticket.status == "open" and ticket.closed_at is None

    def test_illegal_transition_is_400(self, login, agent, ticket):
        response = login(agent).post(status_url(ticket), {"status": "resolved"}, format="json")  # open -> resolved
        assert response.status_code == 400 and "status" in response.data["error"]["fields"]

    def test_unknown_status_is_400(self, login, agent, ticket):
        assert login(agent).post(status_url(ticket), {"status": "banana"}, format="json").status_code == 400

    def test_customer_cannot_change_status(self, login, customer, ticket):
        assert login(customer).post(status_url(ticket), {"status": "closed"}, format="json").status_code == 403

    def test_service_rejects_same_status(self, agent, ticket):
        with pytest.raises(ValidationError):
            services.change_status(ticket, "open", agent)
        assert Ticket.objects.get(pk=ticket.pk).status == "open"
