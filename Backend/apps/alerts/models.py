"""
Alert — an instance of a rule being triggered.

Each time a rule's condition is breached, one Alert record is created.
The alert lifecycle:  OPEN → ACKNOWLEDGED → RESOLVED
"""

import uuid
from django.db import models
from apps.users.models import User
from apps.rules.models import Rule


class Alert(models.Model):

    class Status(models.TextChoices):
        OPEN           = "OPEN",           "Open"
        ACKNOWLEDGED   = "ACKNOWLEDGED",   "Acknowledged"
        RESOLVED       = "RESOLVED",       "Resolved"
        AUTO_RESOLVED  = "AUTO_RESOLVED",  "Auto-Resolved"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule        = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name="alerts")
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    severity    = models.CharField(max_length=20)  # Copied from rule at trigger time

    # What triggered it
    service          = models.CharField(max_length=100)
    triggered_value  = models.FloatField(help_text="The actual metric value that breached the threshold")
    threshold_value  = models.FloatField(help_text="The rule threshold at time of trigger")
    window_start     = models.DateTimeField()
    window_end       = models.DateTimeField()

    # Summary message shown in the UI and notifications
    message     = models.TextField()

    # Lifecycle
    created_at       = models.DateTimeField(auto_now_add=True)
    acknowledged_at  = models.DateTimeField(null=True, blank=True)
    resolved_at      = models.DateTimeField(null=True, blank=True)
    acknowledged_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_alerts"
    )

    # Notification tracking
    notification_sent    = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["rule", "created_at"]),
            models.Index(fields=["service", "created_at"]),
        ]

    def __str__(self):
        return f"Alert[{self.severity}] {self.rule.name} @ {self.created_at:%Y-%m-%d %H:%M}"