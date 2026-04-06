"""
Log query API endpoints.
All queries go through the LogRepository — no direct ES access in views.
"""

from datetime import datetime, timedelta, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.permissions.rbac import IsViewerOrAbove
from integrations.elasticsearch.log_repository import LogRepository, LogQuery
from integrations.elasticsearch.client import ElasticsearchError
from .serializers import LogQuerySerializer


class LogSearchView(APIView):
    """
    GET /api/v1/logs/search/

    Query parameters:
      - start_time: ISO8601 (default: 1 hour ago)
      - end_time:   ISO8601 (default: now)
      - service:    string
      - level:      ERROR|INFO|WARNING|CRITICAL
      - levels:     comma-separated levels
      - search:     full-text search string
      - trace_id:   string
      - user_id:    string
      - status_code: integer
      - min_duration_ms: float
      - page:       integer (default 1)
      - page_size:  integer (default 50, max 500)
      - sort:       @timestamp (default), level, duration_ms
      - order:      asc|desc (default desc)
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request):
        serializer = LogQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            query = LogQuery(
                start_time=data.get("start_time", datetime.now(timezone.utc) - timedelta(hours=1)),
                end_time=data.get("end_time", datetime.now(timezone.utc)),
                service=data.get("service"),
                level=data.get("level"),
                levels=data.get("levels", []),
                search_text=data.get("search"),
                trace_id=data.get("trace_id"),
                user_id=data.get("user_id"),
                status_code=data.get("status_code"),
                min_duration_ms=data.get("min_duration_ms"),
                page=data.get("page", 1),
                page_size=data.get("page_size", 50),
                sort_field=data.get("sort", "@timestamp"),
                sort_order=data.get("order", "desc"),
            )
        except ValueError as e:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )

        repo = LogRepository()
        try:
            result = repo.search_logs(query)
            return Response(result)
        except ElasticsearchError as e:
            return Response(
                {"error": {"code": "SEARCH_ERROR", "message": str(e)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class LogAggregationsView(APIView):
    """
    GET /api/v1/logs/aggregations/
    Returns data formatted for dashboard charts.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request):
        serializer = LogQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        query = LogQuery(
            start_time=data.get("start_time", datetime.now(timezone.utc) - timedelta(hours=24)),
            end_time=data.get("end_time", datetime.now(timezone.utc)),
            service=data.get("service"),
            level=data.get("level"),
        )

        repo = LogRepository()
        try:
            result = repo.get_log_aggregations(query)
            return Response(result)
        except ElasticsearchError as e:
            return Response({"error": str(e)}, status=503)


class LogTraceView(APIView):
    """
    GET /api/v1/logs/trace/{trace_id}/
    Returns all log entries for a given trace ID (distributed tracing).
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request, trace_id: str):
        repo = LogRepository()
        try:
            logs = repo.get_log_by_trace_id(trace_id)
            return Response({"trace_id": trace_id, "count": len(logs), "logs": logs})
        except ElasticsearchError as e:
            return Response({"error": str(e)}, status=503)