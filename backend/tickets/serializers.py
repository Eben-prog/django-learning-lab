from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from accounts.models import User
from accounts.serializers import UserSummarySerializer
from tickets.models import Comment, Ticket


class TicketSerializer(serializers.ModelSerializer):
    """READ shape: what the API returns for a ticket."""

    created_by = UserSummarySerializer(read_only=True)
    assigned_to = UserSummarySerializer(read_only=True)
    updated_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id", "title", "description", "status", "priority",
            "created_by", "assigned_to", "updated_by",
            "created_at", "updated_at", "closed_at",
        ]
        read_only_fields = fields


class TicketCreateSerializer(serializers.ModelSerializer):
    """WRITE shape for POST /tickets/. The client never supplies created_by or status."""

    class Meta:
        model = Ticket
        fields = ["title", "description", "priority"]

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters.")
        return value.strip()

    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Please describe the problem in at least 10 characters.")
        return value.strip()


class TicketUpdateSerializer(TicketCreateSerializer):
    """PUT/PATCH /tickets/{id}/. Customers: title/description of their own OPEN tickets. Staff: also priority."""

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.is_support_staff:
            if "priority" in attrs:
                raise PermissionDenied("Only support staff can change priority.")
            if self.instance.status != Ticket.Status.OPEN:
                raise serializers.ValidationError({"detail": "You can only edit a ticket while it is open."})
        return attrs


class TicketAssignSerializer(serializers.Serializer):
    # `null` means "unassign". The queryset limits valid IDs to active users; the service checks the role.
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True)


class TicketStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ticket.Status.choices)


class CommentSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "body", "is_internal", "is_system", "created_at"]
        read_only_fields = ["id", "author", "is_system", "created_at"]
