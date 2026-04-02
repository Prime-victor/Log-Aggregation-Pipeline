"""
Celery application configuration.
All task modules are auto-discovered from installed apps.
"""

import os
from celery import Celery
from celery.signals import setup_logging
import structlog

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("log_intelligence_platform")

# Load Celery config from Django settings (CELERY_ prefixed keys)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every installed app
app.autodiscover_tasks()


@setup_logging.connect
def config_logging(**kwargs):
    """Use Django's logging config for Celery workers."""
    from django.conf import settings
    import logging.config
    logging.config.dictConfig(settings.LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Health check task."""
    print(f"Request: {self.request!r}")