from rest_framework import serializers
from .models import Anomaly


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = [
            "id",
            "service",
            "anomaly_type",
            "status",
            "anomaly_score",
            "confidence",
            "description",
            "detected_at",
        ]
