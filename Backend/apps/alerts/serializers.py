from rest_framework import serializers
from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "rule_name",
            "status",
            "severity",
            "service",
            "message",
            "created_at",
        ]
