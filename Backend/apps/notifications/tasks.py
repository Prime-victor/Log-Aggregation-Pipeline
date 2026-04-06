"""
Notification delivery tasks.
Decoupled from rule engine — notifications are delivered asynchronously
so a slow SMTP server never blocks alert creation.
"""

import logging
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="notifications.deliver_alert_notification",
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def deliver_alert_notification(self, alert_id: str):
    """
    Deliver notifications for a triggered alert via all configured channels.
    Channels: email, Slack webhook, generic webhook.
    """
    try:
        from apps.alerts.models import Alert
        from apps.notifications.services import NotificationService

        alert   = Alert.objects.select_related("rule", "rule__created_by").get(id=alert_id)
        service = NotificationService()
        service.send_alert(alert)

        # Mark as delivered
        alert.notification_sent    = True
        alert.notification_sent_at = timezone.now()
        alert.save(update_fields=["notification_sent", "notification_sent_at"])

    except Exception as exc:
        logger.error(f"Notification delivery failed for alert {alert_id}: {exc}", exc_info=True)
        # Retry with exponential backoff: 60s, 120s, 240s, 480s, 960s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    name="anomalies.poll_ai_service",
    max_retries=3,
)
def poll_ai_service_for_anomalies(self):
    """
    Periodically call the AI microservice to detect anomalies.
    Runs every 5 minutes (configured in Celery Beat).
    """
    try:
        import httpx
        from django.conf import settings
        from apps.anomalies.models import Anomaly
        from datetime import datetime, timezone

        url = f"{settings.AI_SERVICE_URL}/detect"

        with httpx.Client(timeout=settings.AI_SERVICE_TIMEOUT) as client:
            response = client.post(url, json={"window_minutes": 5})
            response.raise_for_status()
            anomalies = response.json().get("anomalies", [])

        # Persist detected anomalies
        created = 0
        for a in anomalies:
            _, was_created = Anomaly.objects.get_or_create(
                service      = a["service"],
                detected_at  = datetime.fromisoformat(a["detected_at"]),
                anomaly_type = a["type"],
                defaults={
                    "anomaly_score": a["score"],
                    "confidence":    a["confidence"],
                    "description":   a["description"],
                    "window_start":  datetime.fromisoformat(a["window_start"]),
                    "window_end":    datetime.fromisoformat(a["window_end"]),
                    "features":      a.get("features", {}),
                }
            )
            if was_created:
                created += 1

        logger.info(f"Anomaly poll: {len(anomalies)} detected, {created} new")

    except Exception as exc:
        logger.error(f"Anomaly polling failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)