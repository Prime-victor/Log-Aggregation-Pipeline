"""
Injects a unique request_id into every request.
Used for log correlation — the same ID appears in:
  - HTTP response header (X-Request-ID)
  - Structured log entries
  - Exception reports
"""

import uuid
import structlog


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Use client-provided ID (for distributed tracing) or generate one
        request_id = (
            request.headers.get("X-Request-ID")
            or request.META.get("HTTP_X_REQUEST_ID")
            or str(uuid.uuid4())
        )
        request.request_id = request_id

        # Bind to structlog context so all log calls in this request include it
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = self.get_response(request)

        # Echo back so clients can trace their request in our logs
        response["X-Request-ID"] = request_id

        structlog.contextvars.unbind_contextvars("request_id")
        return response