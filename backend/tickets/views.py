from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsSupportStaff
from tickets import services
from tickets.filters import TicketFilter
from tickets.models import Ticket
from tickets.permissions import TicketObjectPermission
from tickets.serializers import (
    CommentSerializer,
    TicketAssignSerializer,
    TicketCreateSerializer,
    TicketSerializer,
    TicketStatusSerializer,
    TicketUpdateSerializer,
)


class TicketViewSet(viewsets.ModelViewSet):
    """
    One class, many routes (the router in urls.py builds them):
      GET    /tickets/            list      POST   /tickets/            create
      GET    /tickets/{id}/       retrieve  PUT/PATCH /tickets/{id}/    update     DELETE /tickets/{id}/  destroy
      POST   /tickets/{id}/assign/   POST /tickets/{id}/status/   GET|POST /tickets/{id}/comments/
    Java analogy: a Spring @RestController with @GetMapping/@PostMapping methods.
    """

    permission_classes = [IsAuthenticated, TicketObjectPermission]
    filterset_class = TicketFilter
    search_fields = ["title", "description", "created_by__username"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # OpenAPI schema generation has no real user
            return Ticket.objects.none()
        # select_related -> one SQL JOIN instead of 3 extra queries per ticket (the "N+1 problem").
        queryset = Ticket.objects.select_related("created_by", "assigned_to", "updated_by")
        user = self.request.user
        if user.is_support_staff:
            return queryset
        return queryset.filter(created_by=user)  # customers can't even see that other tickets exist (404)

    def get_serializer_class(self):
        if self.action == "create":
            return TicketCreateSerializer
        if self.action in ("update", "partial_update"):
            return TicketUpdateSerializer
        return TicketSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdminRole()]
        return super().get_permissions()

    def _ticket_response(self, ticket, http_status=status.HTTP_200_OK):
        ticket = self.get_queryset().get(pk=ticket.pk)  # re-read with joins so nested users are fresh
        return Response(TicketSerializer(ticket, context=self.get_serializer_context()).data, status=http_status)

    @extend_schema(request=TicketCreateSerializer, responses={201: TicketSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(created_by=request.user, updated_by=request.user)  # audit fields set server-side
        return self._ticket_response(ticket, status.HTTP_201_CREATED)

    @extend_schema(request=TicketUpdateSerializer, responses={200: TicketSerializer})
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)  # PATCH -> True, PUT -> False
        ticket = self.get_object()  # 404 if hidden from this user; then object permissions run
        serializer = self.get_serializer(ticket, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(updated_by=request.user)
        return self._ticket_response(ticket)

    @extend_schema(request=TicketAssignSerializer, responses={200: TicketSerializer})
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsSupportStaff])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.assign_ticket(ticket, serializer.validated_data["assigned_to"], request.user)
        return self._ticket_response(ticket)

    @extend_schema(request=TicketStatusSerializer, responses={200: TicketSerializer})
    @action(detail=True, methods=["post"], url_path="status", permission_classes=[IsAuthenticated, IsSupportStaff])
    def set_status(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.change_status(ticket, serializer.validated_data["status"], request.user)
        return self._ticket_response(ticket)

    @extend_schema(request=CommentSerializer, responses={200: CommentSerializer(many=True), 201: CommentSerializer})
    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = services.add_comment(
                ticket, request.user, serializer.validated_data["body"], serializer.validated_data.get("is_internal", False)
            )
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

        queryset = ticket.comments.select_related("author")
        if not request.user.is_support_staff:
            queryset = queryset.filter(is_internal=False)  # customers never see internal notes
        return Response(CommentSerializer(queryset, many=True).data)
