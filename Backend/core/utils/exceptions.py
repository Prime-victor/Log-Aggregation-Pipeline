"""
Unified error response format.

All API errors follow this shape:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Request data is invalid",
        "details": { "field": ["error message"] },
        "request_id": "abc-123"
    }
}
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # First, get the default DRF response
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get("request")
        request_id = getattr(request, "request_id", "unknown") if request else "unknown"

        error_payload = {
            "error": {
                "code": _get_error_code(exc),
                "message": _get_error_message(response),
                "details": response.data if isinstance(response.data, dict) else {},
                "request_id": request_id,
            }
        }

        if response.status_code >= 500:
            logger.error("Server error", exc_info=exc, extra={"request_id": request_id})

        response.data = error_payload

    return response


def _get_error_code(exc) -> str:
    from rest_framework.exceptions import (
        AuthenticationFailed, NotAuthenticated, PermissionDenied,
        NotFound, ValidationError, Throttled
    )
    mapping = {
        AuthenticationFailed: "AUTHENTICATION_FAILED",
        NotAuthenticated:     "NOT_AUTHENTICATED",
        PermissionDenied:     "PERMISSION_DENIED",
        NotFound:             "NOT_FOUND",
        ValidationError:      "VALIDATION_ERROR",
        Throttled:            "RATE_LIMITED",
    }
    return mapping.get(type(exc), "INTERNAL_ERROR")


def _get_error_message(response) -> str:
    data = response.data
    if isinstance(data, list) and data:
        return str(data[0])
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        first_key = next(iter(data), None)
        if first_key:
            val = data[first_key]
            return f"{first_key}: {val[0] if isinstance(val, list) else val}"
    return "An unexpected error occurred."