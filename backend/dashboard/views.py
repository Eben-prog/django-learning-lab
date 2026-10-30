from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.services import ticket_stats


class DashboardView(APIView):
    """GET /api/dashboard/ - statistics scoped to what the caller may see."""

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(ticket_stats(request.user))
