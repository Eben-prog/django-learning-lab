"""
One error format for the whole API:

    {"error": {"status": 400, "code": "validation_error", "message": "...", "fields": {"title": ["..."]}}}

The React app parses exactly this shape (see frontend/src/api/errors.ts).
"""
import logging

from django.db import DatabaseError, IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def error_body(status_code: int, code: str, message: str, fields: dict | None = None) -> dict:
    body = {"error": {"status": status_code, "code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return body


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)  # DRF's default: handles APIException, Http404, PermissionDenied

    if response is None:
        if isinstance(exc, DatabaseError):  # IntegrityError is a subclass of DatabaseError
            # Log the real cause for developers; tell the client nothing sensitive.
            logger.exception("Database error in %s", type(context.get("view")).__name__)
            code = "integrity_error" if isinstance(exc, IntegrityError) else "database_error"
            return Response(error_body(500, code, "A database error occurred. Please try again."), status=500)
        return None  # anything else: Django logs it and returns its own 500 (debug page when DEBUG=True)

    if isinstance(exc, ValidationError):
        fields = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
        response.data = error_body(400, "validation_error", "Some fields are invalid.", fields)
    else:
        detail = response.data.get("detail", "Request failed.") if isinstance(response.data, dict) else str(response.data)
        code = getattr(exc, "default_code", "error")
        response.data = error_body(response.status_code, code, str(detail))
    return response
