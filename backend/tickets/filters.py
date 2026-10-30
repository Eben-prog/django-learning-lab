import django_filters

from tickets.models import Ticket


class TicketFilter(django_filters.FilterSet):
    """?status=open&priority=high&assigned_to=3&unassigned=true&created_after=2026-01-01"""

    unassigned = django_filters.BooleanFilter(method="filter_unassigned")
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Ticket
        fields = ["status", "priority", "assigned_to", "created_by"]

    def filter_unassigned(self, queryset, name, value):
        return queryset.filter(assigned_to__isnull=bool(value))
