"""
Notification Service -- dispatches alerts via multiple channels.

Strategy pattern: each channel is an independent handler.
Adding a new channel (PagerDuty, Teams, SMS) means adding one class.
"""

import logging
import httpx
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.alerts.models import Alert

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "CRITICAL": "!!",
    "HIGH":     "!",
    "MEDIUM":   "~",
    "LOW":      "-",
}

SEVERITY_COLOR = {
    "CRITICAL": "#FF0000",
    "HIGH":     "#FF6600",
    "MEDIUM":   "#FFCC00",
    "LOW":      "#0099FF",
}


class NotificationService:

    def send_alert(self, alert: Alert):
        """Dispatch to all configured channels."""
        if settings.EMAIL_HOST:
            self._send_email(alert)

        if settings.SLACK_WEBHOOK_URL:
            self._send_slack(alert)

    # ---- Email ----

    def _send_email(self, alert: Alert):
        emoji    = SEVERITY_EMOJI.get(alert.severity, "!")
        subject  = f"{emoji} [{alert.severity}] Alert: {alert.rule.name}"

        # Render HTML template
        html_body = render_to_string("notifications/alert_email.html", {
            "alert":  alert,
            "rule":   alert.rule,
            "emoji":  emoji,
        })

        try:
            send_mail(
                subject=subject,
                message=alert.message,   # Plain text fallback
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=self._get_email_recipients(alert),
                html_message=html_body,
                fail_silently=False,
            )
            logger.info(f"Email sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Email delivery failed for alert {alert.id}: {e}")
            raise

    def _get_email_recipients(self, alert: Alert) -> list[str]:
        """In production: look up recipients from rule/team configuration."""
        from apps.users.models import User
        admins_and_analysts = User.objects.filter(
            role__in=["ADMIN", "ANALYST"],
            is_active=True
        ).values_list("email", flat=True)
        return list(admins_and_analysts)

    # ---- Slack ----

    def _send_slack(self, alert: Alert):
        """Send a rich Slack Block Kit message."""
        color = SEVERITY_COLOR.get(alert.severity, "#808080")
        emoji = SEVERITY_EMOJI.get(alert.severity, "!")

        payload = {
            "attachments": [
                {
                    "color":  color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type":  "plain_text",
                                "text":  f"{emoji} {alert.rule.name}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Severity:*\n{alert.severity}"},
                                {"type": "mrkdwn", "text": f"*Service:*\n{alert.service}"},
                                {"type": "mrkdwn", "text": f"*Value:*\n{alert.triggered_value:.2f}"},
                                {"type": "mrkdwn", "text": f"*Threshold:*\n{alert.threshold_value:.2f}"},
                            ]
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*Message:*\n{alert.message}"}
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type":  "button",
                                    "text":  {"type": "plain_text", "text": "View Alert"},
                                    "url":   f"http://your-domain.com/alerts/{alert.id}",
                                    "style": "danger" if alert.severity in ("CRITICAL", "HIGH") else "primary"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(settings.SLACK_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
            logger.info(f"Slack notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Slack delivery failed for alert {alert.id}: {e}")
            raise