from rest_framework import serializers
from .models import Rule


class RuleSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Rule
        fields = [
            "id",
            "name",
            "description",
            "service",
            "condition",
            "operator",
            "threshold",
            "window_sec",
            "severity",
            "is_active",
            "created_at",
            "created_by_email",
        ]
