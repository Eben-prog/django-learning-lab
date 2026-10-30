from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Liveness + database check. First thing to hit when 'nothing works'."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - report any DB failure as 503 without leaking details
        return Response({"status": "error", "database": "unreachable"}, status=503)
    return Response({"status": "ok", "database": "ok"})
