import pytest

from tickets.models import Comment
from tests.conftest import make_ticket


def url(t):
    return f"/api/tickets/{t.id}/comments/"


@pytest.mark.django_db
class TestComments:
    def test_customer_comments_on_own_ticket(self, login, customer, ticket):
        response = login(customer).post(url(ticket), {"body": "Any update?"}, format="json")
        assert response.status_code == 201 and response.data["author"]["id"] == customer.id
        assert Comment.objects.get(pk=response.data["id"]).ticket == ticket

    def test_customer_cannot_comment_on_other_customers_ticket(self, login, customer, other_customer):
        assert login(customer).post(url(make_ticket(other_customer)), {"body": "Hello"}, format="json").status_code == 404

    def test_empty_body_is_400(self, login, customer, ticket):
        for body in ("", "   "):
            response = login(customer).post(url(ticket), {"body": body}, format="json")
            assert response.status_code == 400 and "body" in response.data["error"]["fields"]

    def test_customer_cannot_post_internal_note(self, login, customer, ticket):
        assert login(customer).post(url(ticket), {"body": "secret", "is_internal": True}, format="json").status_code == 403

    def test_internal_notes_are_hidden_from_customers_but_not_agents(self, login, agent, customer, ticket):
        login(agent).post(url(ticket), {"body": "Customer seems confused", "is_internal": True}, format="json")
        login(agent).post(url(ticket), {"body": "We are on it."}, format="json")
        assert [c["body"] for c in login(customer).get(url(ticket)).data] == ["We are on it."]
        assert len(login(agent).get(url(ticket)).data) == 2

    def test_cannot_comment_on_closed_ticket(self, login, customer, ticket):
        ticket.status = "closed"
        ticket.save()
        assert login(customer).post(url(ticket), {"body": "One more thing"}, format="json").status_code == 400

    def test_comments_are_oldest_first(self, login, customer, ticket):
        client = login(customer)
        for text in ("first", "second", "third"):
            client.post(url(ticket), {"body": text}, format="json")
        assert [c["body"] for c in client.get(url(ticket)).data] == ["first", "second", "third"]
