from rest_framework import serializers
from .models import Rule


class RuleSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model  = Rule
        fields = [
            "id", "name", "description", "service",
            "condition", "operator", "threshold", "window_sec",
            "severity", "cooldown_sec", "is_active",
            "created_by_email", "created_at", "updated_at",
            "last_evaluated_at", "last_triggered_at", "trigger_count",
        ]
        read_only_fields = [
            "id", "created_by_email", "created_at", "updated_at",
            "last_evaluated_at", "last_triggered_at", "trigger_count",
        ]

    def validate_window_sec(self, value):
        if value < 60:
            raise serializers.ValidationError("Window must be at least 60 seconds")
        if value > 86400:
            raise serializers.ValidationError("Window cannot exceed 24 hours")
        return value

    def validate_threshold(self, value):
        if value < 0:
            raise serializers.ValidationError("Threshold must be non-negative")
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)