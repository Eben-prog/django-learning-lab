"""Dashboard numbers come from real aggregate queries (GROUP BY / COUNT FILTER), never hard-coded."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from tickets.models import Ticket


def ticket_stats(user) -> dict:
    staff = user.is_support_staff
    tickets = Ticket.objects.all() if staff else Ticket.objects.filter(created_by=user)

    # ONE query: SELECT COUNT(*), COUNT(*) FILTER (WHERE status='open'), ... FROM tickets_ticket WHERE ...
    totals = tickets.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status=Ticket.Status.OPEN)),
        in_progress=Count("id", filter=Q(status=Ticket.Status.IN_PROGRESS)),
        resolved=Count("id", filter=Q(status=Ticket.Status.RESOLVED)),
        closed=Count("id", filter=Q(status=Ticket.Status.CLOSED)),
        created_last_7_days=Count("id", filter=Q(created_at__gte=timezone.now() - timedelta(days=7))),
        unassigned=Count("id", filter=Q(assigned_to__isnull=True) & ~Q(status=Ticket.Status.CLOSED)),
    )

    # Second query: SELECT priority, COUNT(*) ... GROUP BY priority. order_by() clears the default ordering.
    grouped = {row["priority"]: row["n"] for row in tickets.order_by().values("priority").annotate(n=Count("id"))}
    by_priority = {value: grouped.get(value, 0) for value, _ in Ticket.Priority.choices}  # zero-fill missing groups

    return {
        "scope": "all" if staff else "own",
        "total": totals["total"],
        "by_status": {key: totals[key] for key in ("open", "in_progress", "resolved", "closed")},
        "by_priority": by_priority,
        "created_last_7_days": totals["created_last_7_days"],
        "unassigned": totals["unassigned"] if staff else None,
        "assigned_to_me": (
            Ticket.objects.filter(assigned_to=user).exclude(status=Ticket.Status.CLOSED).count() if staff else None
        ),
    }
