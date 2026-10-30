"""Ticket CRUD, ownership, validation, filtering and pagination (API integration tests: HTTP in, DB assertions out)."""
import pytest

from tickets.models import Ticket
from tests.conftest import make_ticket

URL = "/api/tickets/"


@pytest.mark.django_db
class TestCreate:
    def test_customer_creates_ticket_and_it_is_persisted(self, login, customer):
        payload = {"title": "Cannot print invoices", "description": "Invoices print as blank pages.", "priority": "high"}
        response = login(customer).post(URL, payload, format="json")
        assert response.status_code == 201
        row = Ticket.objects.get(pk=response.data["id"])  # really in PostgreSQL
        assert (row.created_by, row.updated_by, row.status, row.priority) == (customer, customer, "open", "high")
        assert response.data["created_by"]["username"] == "cust"

    def test_client_cannot_spoof_creator_or_status(self, login, customer, other_customer):
        payload = {"title": "Sneaky ticket", "description": "Trying to spoof fields.", "created_by": other_customer.id, "status": "closed"}
        response = login(customer).post(URL, payload, format="json")
        assert response.status_code == 201
        assert response.data["created_by"]["id"] == customer.id and response.data["status"] == "open"

    @pytest.mark.parametrize(
        "payload,field",
        [
            ({"title": "abc", "description": "long enough description"}, "title"),
            ({"title": "Good title", "description": "short"}, "description"),
            ({"description": "long enough description"}, "title"),
            ({"title": "Good title", "description": "long enough description", "priority": "extreme"}, "priority"),
        ],
    )
    def test_validation_errors_name_the_field(self, login, customer, payload, field):
        response = login(customer).post(URL, payload, format="json")
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert field in response.data["error"]["fields"]

    def test_anonymous_gets_401(self, api):
        assert api.post(URL, {"title": "x" * 6, "description": "y" * 12}, format="json").status_code == 401


@pytest.mark.django_db
class TestVisibilityAndPermissions:
    def test_customer_lists_only_own_tickets(self, login, customer, other_customer):
        make_ticket(customer, title="Mine mine mine")
        make_ticket(other_customer, title="Not yours")
        response = login(customer).get(URL)
        assert [t["title"] for t in response.data["results"]] == ["Mine mine mine"]

    def test_agent_sees_everything(self, login, agent, customer, other_customer):
        make_ticket(customer)
        make_ticket(other_customer)
        assert login(agent).get(URL).data["count"] == 2

    def test_customer_gets_404_for_someone_elses_ticket(self, login, customer, other_customer):
        theirs = make_ticket(other_customer)
        assert login(customer).get(f"{URL}{theirs.id}/").status_code == 404

    def test_unknown_ticket_is_404_with_envelope(self, login, agent):
        response = login(agent).get(f"{URL}999999/")
        assert response.status_code == 404 and response.data["error"]["status"] == 404

    def test_customer_cannot_edit_someone_elses_ticket(self, login, customer, other_customer):
        theirs = make_ticket(other_customer)
        assert login(customer).patch(f"{URL}{theirs.id}/", {"title": "Hijacked title"}, format="json").status_code == 404
        theirs.refresh_from_db()
        assert theirs.title != "Hijacked title"


@pytest.mark.django_db
class TestUpdateAndDelete:
    def test_owner_can_patch_title_while_open(self, login, customer, ticket):
        response = login(customer).patch(f"{URL}{ticket.id}/", {"title": "Printer really on fire"}, format="json")
        assert response.status_code == 200 and response.data["title"] == "Printer really on fire"
        ticket.refresh_from_db()
        assert ticket.updated_by == customer

    def test_owner_cannot_change_priority(self, login, customer, ticket):
        assert login(customer).patch(f"{URL}{ticket.id}/", {"priority": "urgent"}, format="json").status_code == 403

    def test_owner_cannot_edit_after_work_started(self, login, customer, ticket):
        ticket.status = "in_progress"
        ticket.save()
        assert login(customer).patch(f"{URL}{ticket.id}/", {"title": "Changed my mind"}, format="json").status_code == 400

    def test_agent_can_change_priority_and_is_recorded_as_updater(self, login, agent, ticket):
        response = login(agent).patch(f"{URL}{ticket.id}/", {"priority": "urgent"}, format="json")
        assert response.status_code == 200 and response.data["updated_by"]["id"] == agent.id

    def test_put_requires_full_representation(self, login, agent, ticket):
        assert login(agent).put(f"{URL}{ticket.id}/", {"title": "Only a title"}, format="json").status_code == 400
        full = {"title": "Replaced title", "description": "Replaced description text", "priority": "low"}
        assert login(agent).put(f"{URL}{ticket.id}/", full, format="json").status_code == 200

    def test_only_admin_can_delete(self, login, customer, agent, admin_user, ticket):
        assert login(customer).delete(f"{URL}{ticket.id}/").status_code == 403
        assert login(agent).delete(f"{URL}{ticket.id}/").status_code == 403
        assert login(admin_user).delete(f"{URL}{ticket.id}/").status_code == 204
        assert not Ticket.objects.filter(pk=ticket.id).exists()


@pytest.mark.django_db
class TestListingFilteringPagination:
    def test_pagination_metadata_and_second_page(self, login, agent, customer):
        for i in range(12):
            make_ticket(customer, title=f"Ticket number {i:02d}")
        client = login(agent)
        first = client.get(URL)
        assert first.data["count"] == 12 and len(first.data["results"]) == 10 and first.data["next"]
        assert len(client.get(URL, {"page": 2}).data["results"]) == 2

    def test_out_of_range_page_is_404(self, login, agent, customer):
        make_ticket(customer)
        assert login(agent).get(URL, {"page": 99}).status_code == 404  # DRF: "Invalid page."

    def test_filter_by_status_priority_and_unassigned(self, login, agent, customer):
        make_ticket(customer, title="Open and low", priority="low")
        make_ticket(customer, title="Busy and high", priority="high", status="in_progress", assigned_to=agent)
        client = login(agent)
        assert [t["title"] for t in client.get(URL, {"status": "in_progress"}).data["results"]] == ["Busy and high"]
        assert [t["title"] for t in client.get(URL, {"priority": "low"}).data["results"]] == ["Open and low"]
        assert [t["title"] for t in client.get(URL, {"unassigned": "true"}).data["results"]] == ["Open and low"]

    def test_invalid_filter_value_is_400(self, login, agent):
        assert login(agent).get(URL, {"status": "banana"}).status_code == 400

    def test_search_matches_title_and_description(self, login, agent, customer):
        make_ticket(customer, title="Refund missing", description="Money never came back.")
        make_ticket(customer, title="Other thing", description="Nothing relevant here.")
        assert login(agent).get(URL, {"search": "refund"}).data["count"] == 1
        assert login(agent).get(URL, {"search": "never came"}).data["count"] == 1

    def test_list_uses_constant_number_of_queries(self, login, agent, customer, django_assert_max_num_queries):
        """Regression guard against the N+1 query problem (select_related in TicketViewSet.get_queryset)."""
        for _ in range(8):
            make_ticket(customer, assigned_to=agent)
        client = login(agent)
        with django_assert_max_num_queries(4):  # COUNT(*) + SELECT ... JOIN ...
            assert client.get(URL).status_code == 200
