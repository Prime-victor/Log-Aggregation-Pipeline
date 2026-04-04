"""
Singleton Elasticsearch client with connection pooling.

Why a singleton? Creating an ES client is expensive (DNS lookups, connection
pools). Re-use one instance across the Django process lifetime.

This module is the ONLY place that imports elasticsearch — all other code
goes through this interface. This makes swapping ES versions or mocking in
tests trivial.
"""

import logging
from functools import lru_cache
from typing import Any

from elasticsearch import Elasticsearch, NotFoundError, RequestError
from django.conf import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_es_client() -> Elasticsearch:
    """
    Return a cached Elasticsearch client instance.
    lru_cache(1) ensures we never create more than one client per process.
    """
    config = settings.ELASTICSEARCH
    client = Elasticsearch(
        hosts=config["HOSTS"],
        request_timeout=config.get("TIMEOUT", 30),
        max_retries=config.get("MAX_RETRIES", 3),
        retry_on_timeout=config.get("RETRY_ON_TIMEOUT", True),
        # In production with security enabled:
        # http_auth=("user", "password"),
        # scheme="https",
        # verify_certs=True,
        # ca_certs="/path/to/ca.crt",
    )
    logger.info("Elasticsearch client initialized", extra={"hosts": config["HOSTS"]})
    return client


class ElasticsearchError(Exception):
    """Raised when an ES operation fails in a way that should surface to the API."""
    pass