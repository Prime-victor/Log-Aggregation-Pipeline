from rest_framework import serializers


class CommaSeparatedListField(serializers.ListField):
    """
    Accept either a list or a comma-separated string for query params.
    """

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [item.strip() for item in data.split(",") if item.strip()]
        return super().to_internal_value(data)


class LogQuerySerializer(serializers.Serializer):
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    service = serializers.CharField(required=False, allow_blank=True)

    level = serializers.CharField(required=False, allow_blank=True)
    levels = CommaSeparatedListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    search = serializers.CharField(required=False, allow_blank=True)
    trace_id = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.CharField(required=False, allow_blank=True)
    status_code = serializers.IntegerField(required=False)
    min_duration_ms = serializers.FloatField(required=False)

    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=500, default=50)
    sort = serializers.CharField(required=False, allow_blank=True)
    order = serializers.ChoiceField(required=False, choices=["asc", "desc"], default="desc")

    def validate_level(self, value):
        if not value:
            return value
        return value.upper()

    def validate_levels(self, value):
        return [v.upper() for v in value]

    def validate(self, attrs):
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("start_time must be before end_time")
        return attrs
