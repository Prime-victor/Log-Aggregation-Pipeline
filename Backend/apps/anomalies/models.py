"""
Anomaly — detected by the AI/ML microservice (Isolation Forest).
Stored separately from rule-based alerts to allow different workflows.
"""

import uuid
from django.db import models


class Anomaly(models.Model):

    class AnomalyType(models.TextChoices):
        VOLUME_SPIKE   = "VOLUME_SPIKE",   "Volume Spike"
        ERROR_BURST    = "ERROR_BURST",    "Error Burst"
        LATENCY_SPIKE  = "LATENCY_SPIKE",  "Latency Spike"
        UNUSUAL_PATTERN = "UNUSUAL_PATTERN", "Unusual Pattern"

    class Status(models.TextChoices):
        NEW        = "NEW",        "New"
        CONFIRMED  = "CONFIRMED",  "Confirmed"
        DISMISSED  = "DISMISSED",  "Dismissed"

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service         = models.CharField(max_length=100)
    anomaly_type    = models.CharField(max_length=30, choices=AnomalyType.choices)
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    # ML score: how anomalous (0.0 = normal, 1.0 = maximally anomalous)
    anomaly_score   = models.FloatField()
    confidence      = models.FloatField(help_text="Model confidence (0.0–1.0)")

    description     = models.TextField()
    detected_at     = models.DateTimeField()
    window_start    = models.DateTimeField()
    window_end      = models.DateTimeField()

    # Raw feature values used by the model (for explainability)
    features        = models.JSONField(default=dict)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "anomalies"
        ordering = ["-detected_at"]
        indexes  = [
            models.Index(fields=["service", "detected_at"]),
            models.Index(fields=["status", "anomaly_score"]),
        ]