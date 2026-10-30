"""
AUTHENTICATION answers "who are you?" (JWT -> request.user).
AUTHORIZATION answers "are you allowed to do this?" (these classes).
Failing the first gives 401; failing the second gives 403.
"""
from rest_framework.permissions import BasePermission


class IsSupportStaff(BasePermission):
    """Agents and administrators."""

    message = "Only support agents and administrators can do this."

    def has_permission(self, request, view):
        user = request.user
        # `is_authenticated` first: AnonymousUser has no `is_support_staff` attribute.
        return bool(user and user.is_authenticated and user.is_support_staff)


class IsAdminRole(BasePermission):
    message = "Only administrators can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)
