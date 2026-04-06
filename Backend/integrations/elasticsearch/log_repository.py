"""
Log Repository — single source of truth for all Elasticsearch queries.

Architecture principle: Views call repositories, not ES directly.
This decoupling means:
  - Easy to unit-test (mock the repository)
  - Easy to add caching
  - Easy to swap ES for another store if needed
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from elasticsearch import NotFoundError
from elasticsearch.helpers import scan

from integrations.elasticsearch.client import get_es_client, ElasticsearchError
from integrations.elasticsearch.indexes import get_log_index_pattern

logger = logging.getLogger(__name__)


@dataclass
class LogQuery:
    """
    Immutable value object representing a log search query.
    Validated before being passed to the repository.
    """
    # Time range (required)
    start_time: datetime
    end_time:   datetime

    # Optional filters
    service:    Optional[str]  = None
    level:      Optional[str]  = None      # ERROR, INFO, WARNING, CRITICAL
    trace_id:   Optional[str]  = None
    user_id:    Optional[str]  = None
    search_text: Optional[str] = None      # Full-text search on log_message
    status_code: Optional[int] = None
    min_duration_ms: Optional[float] = None

    # Pagination
    page:       int = 1
    page_size:  int = 50

    # Sorting
    sort_field: str = "@timestamp"
    sort_order: str = "desc"

    # Additional level filters (multi-select)
    levels: list = field(default_factory=list)

    def __post_init__(self):
        if self.page_size > 500:
            raise ValueError("page_size cannot exceed 500")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        if self.sort_order not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")


class LogRepository:
    """
    Elasticsearch query implementation for log data.
    All methods return plain Python dicts/lists (not ES response objects).
    """

    def __init__(self):
        self.es = get_es_client()

    def search_logs(self, query: LogQuery) -> dict:
        """
        Main search method: returns paginated log results.

        Uses `from/size` for pages up to 10,000 results.
        For deeper pagination, use `search_after` (see search_logs_after).
        """
        try:
            es_query = self._build_query(query)
            from_offset = (query.page - 1) * query.page_size

            response = self.es.search(
                index=get_log_index_pattern(query.service or "*"),
                body={
                    "query": es_query,
                    "from":  from_offset,
                    "size":  query.page_size,
                    "sort":  [
                        {query.sort_field: {"order": query.sort_order}},
                        {"_id": "asc"},          # Tie-breaker for stable pagination
                    ],
                    "_source": True,
                    "track_total_hits": True,    # Exact count (slower for >10k hits)
                },
                request_timeout=30,
            )

            hits      = response["hits"]["hits"]
            total     = response["hits"]["total"]["value"]
            total_pages = (total + query.page_size - 1) // query.page_size

            return {
                "total":       total,
                "page":        query.page,
                "page_size":   query.page_size,
                "total_pages": total_pages,
                "results":     [self._format_hit(h) for h in hits],
            }

        except Exception as e:
            logger.error("Elasticsearch search failed", exc_info=e)
            raise ElasticsearchError(f"Search failed: {e}") from e

    def get_log_aggregations(self, query: LogQuery) -> dict:
        """
        Returns aggregations for charting:
          - Log volume over time (histogram)
          - Level distribution (pie chart)
          - Top error messages
          - Top slow services (P99 latency)
        """
        es_query = self._build_query(query)

        # Determine histogram interval based on time range
        duration_hours = (query.end_time - query.start_time).total_seconds() / 3600
        if duration_hours <= 1:
            interval = "1m"
        elif duration_hours <= 24:
            interval = "30m"
        elif duration_hours <= 168:   # 1 week
            interval = "6h"
        else:
            interval = "1d"

        response = self.es.search(
            index=get_log_index_pattern(query.service or "*"),
            body={
                "query": es_query,
                "size": 0,               # We only want aggregations, not hits
                "aggs": {
                    # Log volume timeline
                    "volume_over_time": {
                        "date_histogram": {
                            "field":             "@timestamp",
                            "calendar_interval": interval,
                            "time_zone":         "UTC",
                        },
                        "aggs": {
                            "by_level": {
                                "terms": {"field": "level", "size": 10}
                            }
                        }
                    },
                    # Level distribution
                    "level_distribution": {
                        "terms": {"field": "level", "size": 10}
                    },
                    # Top error messages
                    "top_errors": {
                        "filter": {"term": {"level": "ERROR"}},
                        "aggs": {
                            "messages": {
                                "terms": {
                                    "field": "error_message.keyword",
                                    "size":  10
                                }
                            }
                        }
                    },
                    # P99 latency per service
                    "latency_by_service": {
                        "terms": {"field": "service", "size": 20},
                        "aggs": {
                            "p99_latency": {
                                "percentiles": {
                                    "field":    "duration_ms",
                                    "percents": [50, 95, 99],
                                }
                            }
                        }
                    },
                    # Error rate = errors / total (useful for alerting dashboard)
                    "error_rate": {
                        "filters": {
                            "filters": {
                                "errors": {"terms": {"level": ["ERROR", "CRITICAL"]}},
                                "total":  {"match_all": {}},
                            }
                        }
                    }
                }
            },
        )

        return self._format_aggregations(response["aggregations"])

    def get_log_by_trace_id(self, trace_id: str, limit: int = 100) -> list:
        """
        Retrieve all log entries for a distributed trace.
        This is the entry point for distributed tracing support.
        """
        response = self.es.search(
            index=get_log_index_pattern(),
            body={
                "query": {"term": {"trace_id": trace_id}},
                "sort": [{"@timestamp": "asc"}],
                "size": limit,
            }
        )
        return [self._format_hit(h) for h in response["hits"]["hits"]]

    def get_error_rate(self, service: str, window_seconds: int) -> float:
        """
        Used by the rule engine to evaluate error_rate conditions.
        Returns percentage of ERROR/CRITICAL logs in the window.
        """
        now   = datetime.now(timezone.utc)
        start = now.timestamp() - window_seconds

        response = self.es.search(
            index=get_log_index_pattern(service),
            body={
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"@timestamp": {
                                "gte": f"{int(start * 1000)}",   # epoch_millis
                                "lte": "now",
                                "format": "epoch_millis"
                            }}},
                            *(
                                [{"term": {"service": service}}]
                                if service else []
                            )
                        ]
                    }
                },
                "size": 0,
                "aggs": {
                    "total":  {"value_count": {"field": "@timestamp"}},
                    "errors": {
                        "filter": {
                            "terms": {"level": ["ERROR", "CRITICAL"]}
                        }
                    }
                }
            }
        )

        aggs  = response["aggregations"]
        total = aggs["total"]["value"]
        if total == 0:
            return 0.0
        errors = aggs["errors"]["doc_count"]
        return round((errors / total) * 100, 2)

    def get_log_count(self, service: str, window_seconds: int,
                       level: str = None) -> int:
        """Log count in window. Used by rule engine."""
        start = datetime.now(timezone.utc).timestamp() - window_seconds

        must_filters = [
            {"range": {"@timestamp": {
                "gte": int(start * 1000), "format": "epoch_millis"
            }}}
        ]
        if service:
            must_filters.append({"term": {"service": service}})
        if level:
            must_filters.append({"term": {"level": level.upper()}})

        response = self.es.count(
            index=get_log_index_pattern(service),
            body={"query": {"bool": {"filter": must_filters}}}
        )
        return response["count"]

    # ─── Private Helpers ──────────────────────────────────────────────────────

    def _build_query(self, query: LogQuery) -> dict:
        """Translate LogQuery value object → ES bool query DSL."""

        must_filters = [
            {
                "range": {
                    "@timestamp": {
                        "gte": query.start_time.isoformat(),
                        "lte": query.end_time.isoformat(),
                    }
                }
            }
        ]

        if query.service:
            must_filters.append({"term": {"service": query.service}})

        # Single level OR multiple levels
        if query.level:
            must_filters.append({"term": {"level": query.level.upper()}})
        elif query.levels:
            must_filters.append({"terms": {"level": [l.upper() for l in query.levels]}})

        if query.trace_id:
            must_filters.append({"term": {"trace_id": query.trace_id}})

        if query.user_id:
            must_filters.append({"term": {"user_id": query.user_id}})

        if query.status_code is not None:
            must_filters.append({"term": {"status_code": query.status_code}})

        if query.min_duration_ms is not None:
            must_filters.append({
                "range": {"duration_ms": {"gte": query.min_duration_ms}}
            })

        # Full-text search — uses analyzed fields
        if query.search_text:
            return {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query":  query.search_text,
                            "fields": [
                                "log_message^3",     # Boost main message
                                "error_message^2",
                                "stack_trace",
                                "request_path",
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",     # Typo-tolerant search
                        }
                    },
                    "filter": must_filters,
                }
            }

        return {"bool": {"filter": must_filters}}

    def _format_hit(self, hit: dict) -> dict:
        """Flatten ES hit into a clean dict for the API response."""
        source = hit.get("_source", {})
        return {
            "id":           hit["_id"],
            "index":        hit["_index"],
            "timestamp":    source.get("@timestamp"),
            "level":        source.get("level"),
            "severity":     source.get("severity"),
            "service":      source.get("service"),
            "message":      source.get("log_message") or source.get("message"),
            "error":        source.get("error_message"),
            "trace_id":     source.get("trace_id"),
            "user_id":      source.get("user_id"),
            "status_code":  source.get("status_code"),
            "duration_ms":  source.get("duration_ms"),
            "request_path": source.get("request_path"),
            "http_method":  source.get("http_method"),
            "environment":  source.get("environment"),
            "raw":          source,   # Full source for detail view
        }

    def _format_aggregations(self, aggs: dict) -> dict:
        """Transform ES aggregation response into chart-ready format."""
        volume_buckets = aggs.get("volume_over_time", {}).get("buckets", [])

        return {
            "volume_over_time": [
                {
                    "timestamp": b["key_as_string"],
                    "total":     b["doc_count"],
                    "by_level":  {
                        lvl["key"]: lvl["doc_count"]
                        for lvl in b.get("by_level", {}).get("buckets", [])
                    }
                }
                for b in volume_buckets
            ],
            "level_distribution": {
                b["key"]: b["doc_count"]
                for b in aggs.get("level_distribution", {}).get("buckets", [])
            },
            "top_errors": [
                {"message": b["key"], "count": b["doc_count"]}
                for b in aggs.get("top_errors", {}).get("messages", {}).get("buckets", [])
            ],
            "latency_by_service": [
                {
                    "service": b["key"],
                    "p50":     b.get("p99_latency", {}).get("values", {}).get("50.0"),
                    "p95":     b.get("p99_latency", {}).get("values", {}).get("95.0"),
                    "p99":     b.get("p99_latency", {}).get("values", {}).get("99.0"),
                }
                for b in aggs.get("latency_by_service", {}).get("buckets", [])
            ],
        }