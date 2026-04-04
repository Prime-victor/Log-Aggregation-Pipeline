"""
Index name helpers.

Centralizing index naming here means if we ever change the convention,
we only update one place.
"""

from django.conf import settings
from datetime import datetime, timezone


def get_index_prefix() -> str:
    return settings.ELASTICSEARCH.get("INDEX_PREFIX", "logs")


def get_log_index_pattern(service: str = "*") -> str:
    """
    Returns an index pattern for querying.
    - All services:       logs-*
    - Specific service:   logs-payment-service-*
    """
    prefix = get_index_prefix()
    if service and service != "*":
        return f"{prefix}-{service}-*"
    return f"{prefix}-*"


def get_log_index_name(service: str, dt: datetime = None) -> str:
    """
    Returns the write target index name.
    logs-payment-service-2024.01.15
    """
    prefix = get_index_prefix()
    dt = dt or datetime.now(timezone.utc)
    date_str = dt.strftime("%Y.%m.%d")
    return f"{prefix}-{service}-{date_str}"