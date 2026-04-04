"""
Alert Rules — define conditions that trigger notifications.

Rule schema:
    - service:    which service to watch (null = all)
    - condition:  what to evaluate (error_rate, log_count, latency_p99)
    - threshold:  numeric value to compare against
    - window_sec: rolling time window in seconds
    - operator:   >, >=, <, <=
    - severity:   how critical is a breach

Example rule in English:
    "If error_rate for payment-service exceeds 5% in the last 5 minutes → CRITICAL alert"
"""

import uuid
from django.db import models
from apps.users.models import User


class Rule(models.Model):

    class Condition(models.TextChoices):
        ERROR_RATE     = "error_rate",     "Error Rate (%)"
        LOG_COUNT      = "log_count",      "Log Count"
        LATENCY_P99    = "latency_p99",    "P99 Latency (ms)"
        ERROR_COUNT    = "error_count",    "Error Count"
        CRITICAL_COUNT = "critical_count", "Critical Count"

    class Operator(models.TextChoices):
        GT  = "gt",  ">"
        GTE = "gte", ">="
        LT  = "lt",  "<"
        LTE = "lte", "<="

    class Severity(models.TextChoices):
        LOW      = "LOW",      "Low"
        MEDIUM   = "MEDIUM",   "Medium"
        HIGH     = "HIGH",     "High"
        CRITICAL = "CRITICAL", "Critical"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # What to watch
    service     = models.CharField(max_length=100, blank=True, help_text="Leave blank for all services")
    condition   = models.CharField(max_length=30, choices=Condition.choices)
    operator    = models.CharField(max_length=5, choices=Operator.choices, default=Operator.GT)
    threshold   = models.FloatField()
    window_sec  = models.IntegerField(default=300, help_text="Evaluation window in seconds (default 5 min)")

    # Alert behavior
    severity          = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    cooldown_sec      = models.IntegerField(default=900, help_text="Minimum seconds between repeated alerts")

    # State
    is_active   = models.BooleanField(default=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_rules")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # Tracking
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    trigger_count     = models.IntegerField(default=0)

    class Meta:
        db_table  = "rules"
        ordering  = ["-created_at"]
        indexes   = [
            models.Index(fields=["is_active", "service"]),
        ]

    def __str__(self):
        service_str = self.service or "ALL"
        return f"[{self.severity}] {self.name} — {service_str}"

    def matches_condition(self, value: float) -> bool:
        """Evaluate whether a computed metric value breaches this rule."""
        ops = {
            self.Operator.GT:  lambda v, t: v > t,
            self.Operator.GTE: lambda v, t: v >= t,
            self.Operator.LT:  lambda v, t: v < t,
            self.Operator.LTE: lambda v, t: v <= t,
        }
        return ops[self.operator](value, self.threshold)