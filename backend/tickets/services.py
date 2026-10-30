"""
Business rules that touch several rows at once live here, not in views.

Why a service module at all? `assign_ticket` and `change_status` each (1) validate a rule, (2) update the
ticket and (3) add a system comment. Those writes must succeed or fail TOGETHER, and the same logic is needed
from the API and from tests, so one function wrapped in a transaction is clearer than copy-pasting it into views.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from tickets.models import Comment, Ticket

S = Ticket.Status

# current status -> statuses you may move to. Plain string values keep dict/set lookups unambiguous.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    S.OPEN.value: {S.IN_PROGRESS.value, S.CLOSED.value},
    S.IN_PROGRESS.value: {S.OPEN.value, S.RESOLVED.value, S.CLOSED.value},
    S.RESOLVED.value: {S.IN_PROGRESS.value, S.CLOSED.value},
    S.CLOSED.value: {S.OPEN.value},
}


def _system_comment(ticket: Ticket, actor, text: str) -> None:
    Comment.objects.create(ticket=ticket, author=actor, body=text, is_system=True)


@transaction.atomic  # BEGIN ... COMMIT; any exception inside rolls everything back
def change_status(ticket: Ticket, new_status: str, actor) -> Ticket:
    # SELECT ... FOR UPDATE: lock the row so two agents can't race each other through the state machine.
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    if new_status == ticket.status:
        raise ValidationError({"status": [f"Ticket is already {ticket.status}."]})
    if new_status not in ALLOWED_TRANSITIONS[ticket.status]:
        allowed = ", ".join(sorted(ALLOWED_TRANSITIONS[ticket.status]))
        raise ValidationError({"status": [f"Cannot move from {ticket.status} to {new_status}. Allowed: {allowed}."]})

    old_status = ticket.status
    ticket.status = new_status
    ticket.closed_at = timezone.now() if new_status == S.CLOSED else None
    ticket.updated_by = actor
    ticket.save()
    _system_comment(ticket, actor, f"Status changed from {old_status} to {new_status}.")
    return ticket


@transaction.atomic
def assign_ticket(ticket: Ticket, agent, actor) -> Ticket:
    """Assign to an agent/admin, or unassign when `agent` is None."""
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    if ticket.status == S.CLOSED:
        raise ValidationError({"assigned_to": ["Closed tickets cannot be reassigned. Reopen the ticket first."]})
    if agent is not None and not (agent.is_active and agent.is_support_staff):
        # This rule cannot be a database CHECK (it spans two tables), so the application enforces it.
        raise ValidationError({"assigned_to": ["Tickets can only be assigned to active support agents or administrators."]})

    ticket.assigned_to = agent
    if agent is not None and ticket.status == S.OPEN:
        ticket.status = S.IN_PROGRESS
    ticket.updated_by = actor
    ticket.save()
    _system_comment(ticket, actor, f"Assigned to {agent.username}." if agent else "Ticket unassigned.")
    return ticket


def add_comment(ticket: Ticket, author, body: str, is_internal: bool = False) -> Comment:
    if ticket.status == S.CLOSED:
        raise ValidationError({"detail": "This ticket is closed. Reopen it to add comments."})
    if is_internal and not author.is_support_staff:
        raise PermissionDenied("Customers cannot post internal notes.")
    return Comment.objects.create(ticket=ticket, author=author, body=body, is_internal=is_internal)
