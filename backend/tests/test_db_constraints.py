"""
Tests that go straight to the database layer. They prove the schema protects itself even if
application code (or a hand-typed SQL statement) misbehaves.
"""
import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import User
from tickets.models import Comment, Ticket
from tests.conftest import make_ticket, make_user


@pytest.mark.django_db
class TestTicketConstraints:
    def test_invalid_status_is_rejected_by_postgres(self, customer):
        with pytest.raises(IntegrityError), transaction.atomic():  # atomic() keeps the test transaction usable
            Ticket.objects.create(title="Bad status", description="x" * 12, status="bogus", created_by=customer)

    def test_closed_at_requires_closed_status(self, customer):
        from django.utils import timezone

        with pytest.raises(IntegrityError), transaction.atomic():
            Ticket.objects.create(title="Open with date", description="x" * 12, created_by=customer, closed_at=timezone.now())

    def test_empty_comment_body_is_rejected(self, ticket, customer):
        with pytest.raises(IntegrityError), transaction.atomic():
            Comment.objects.create(ticket=ticket, author=customer, body="")

    def test_foreign_key_to_missing_user_is_rejected(self):
        # PostgreSQL FKs are DEFERRABLE INITIALLY DEFERRED in Django: the INSERT "succeeds" and the violation is
        # reported when constraints are checked (normally at COMMIT). check_constraints() forces that check now.
        with pytest.raises(IntegrityError), transaction.atomic():
            Ticket.objects.create(title="Orphan ticket", description="x" * 12, created_by_id=999999)
            transaction.get_connection().check_constraints()


@pytest.mark.django_db
class TestUserConstraintsAndDeletion:
    def test_duplicate_email_is_rejected(self, customer):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="other", email=customer.email, password="x")

    def test_invalid_role_is_rejected(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            make_user("weird", "wizard")

    def test_cannot_delete_user_who_created_tickets(self, ticket, customer):
        with pytest.raises(ProtectedError):  # on_delete=PROTECT
            customer.delete()

    def test_deleting_an_agent_unassigns_but_keeps_the_ticket(self, customer, agent):
        t = make_ticket(customer, assigned_to=agent)
        agent.delete()  # on_delete=SET_NULL
        t.refresh_from_db()
        assert t.assigned_to is None

    def test_deleting_a_ticket_cascades_to_its_comments(self, ticket, customer):
        Comment.objects.create(ticket=ticket, author=customer, body="hello")
        ticket.delete()
        assert Comment.objects.count() == 0

    def test_superuser_gets_admin_role(self, db):
        user = User.objects.create_superuser(username="root", email="root@example.test", password="x")
        assert user.role == "admin"
