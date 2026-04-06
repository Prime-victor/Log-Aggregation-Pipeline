"""
Extract numerical feature vectors from Elasticsearch log windows.
Each service in a given time window becomes one row in the feature matrix.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")


class FeatureExtractor:

    def __init__(self):
        self.es = Elasticsearch(hosts=[ES_HOST])

    async def extract_current_features(
        self, start: datetime, end: datetime
    ) -> dict[str, list[float]]:
        """
        Extract features for all services in a time window.
        Returns: { "service_name": [f1, f2, f3, f4, f5] }
        """
        services = self._get_active_services(start, end)
        result   = {}

        for service in services:
            features = self._extract_window_features(service, start, end)
            if features is not None:
                result[service] = features

        return result

    async def extract_training_features(self, lookback_hours: int) -> Optional[list]:
        """
        Extract feature matrix for model training.
        Creates one row per (service, 5-minute window) combination.
        Returns a list of feature vectors.
        """
        end   = datetime.now(timezone.utc)
        start = end - timedelta(hours=lookback_hours)

        all_features = []
        services     = self._get_active_services(start, end)

        # Slide a 5-minute window over the entire lookback period
        window_size = timedelta(minutes=5)
        current     = start

        while current < end:
            window_end = current + window_size
            for service in services:
                f = self._extract_window_features(service, current, window_end)
                if f is not None:
                    all_features.append(f)
            current = window_end

        logger.info(f"Extracted {len(all_features)} feature vectors from {len(services)} services")
        return all_features if all_features else None

    def _extract_window_features(
        self, service: str, start: datetime, end: datetime
    ) -> Optional[list[float]]:
        """
        Extract 5 features for a single (service, window) combination.
        Returns None if there's insufficient data.
        """
        try:
            resp = self.es.search(
                index=f"logs-{service}-*",
                body={
                    "query": {
                        "bool": {
                            "filter": [
                                {"range": {"@timestamp": {
                                    "gte": start.isoformat(),
                                    "lte": end.isoformat()
                                }}},
                                {"term": {"service": service}},
                            ]
                        }
                    },
                    "size": 0,
                    "aggs": {
                        "total":    {"value_count": {"field": "@timestamp"}},
                        "errors":   {"filter": {"terms": {"level": ["ERROR", "CRITICAL"]}}},
                        "criticals":{"filter": {"term":  {"level": "CRITICAL"}}},
                        "p99":      {"percentiles": {"field": "duration_ms", "percents": [99]}},
                        "prev_errors": {
                            # Error count in the previous window (for velocity)
                            "filter": {
                                "range": {"@timestamp": {
                                    "gte": (start - (end - start)).isoformat(),
                                    "lt":  start.isoformat(),
                                }}
                            }
                        }
                    }
                }
            )

            aggs         = resp["aggregations"]
            total        = aggs["total"]["value"]
            error_count  = aggs["errors"]["doc_count"]
            critical_count = aggs["criticals"]["doc_count"]
            p99_latency  = aggs["p99"]["values"].get("99.0") or 0.0
            prev_errors  = aggs["prev_errors"]["doc_count"]

            if total < 5:   # Skip windows with too few events
                return None

            error_rate     = (error_count / total * 100) if total > 0 else 0.0
            error_velocity = float(error_count - prev_errors)   # Rate of change
            critical_ratio = (critical_count / error_count) if error_count > 0 else 0.0

            return [error_rate, float(total), p99_latency, error_velocity, critical_ratio]

        except Exception as e:
            logger.warning(f"Feature extraction failed for {service}: {e}")
            return None

    def _get_active_services(self, start: datetime, end: datetime) -> list[str]:
        """Find all services that had log activity in this time range."""
        try:
            resp = self.es.search(
                index="logs-*",
                body={
                    "query": {"range": {"@timestamp": {
                        "gte": start.isoformat(), "lte": end.isoformat()
                    }}},
                    "size": 0,
                    "aggs": {"services": {"terms": {"field": "service", "size": 100}}}
                }
            )
            return [b["key"] for b in resp["aggregations"]["services"]["buckets"]]
        except Exception:
            return []