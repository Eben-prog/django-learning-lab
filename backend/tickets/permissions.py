from rest_framework.permissions import BasePermission


class TicketObjectPermission(BasePermission):
    """
    Object-level rule: support staff may touch any ticket; customers only their own.

    The viewset's get_queryset() already hides other customers' tickets (404), so this is a second,
    independent layer ("defence in depth"): if someone later changes the queryset by mistake, this still says 403.
    """

    message = "You do not have access to this ticket."

    def has_object_permission(self, request, view, obj):
        user = request.user
        return user.is_support_staff or obj.created_by_id == user.id
