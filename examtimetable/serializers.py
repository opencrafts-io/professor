from rest_framework import serializers

from .models import ExamSchedule


class ExamScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for ExamSchedule.
    """

    raw_data = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = ExamSchedule
        fields = [
            "course_code",
            "semester",
            "start_time",
            "end_time",
            "venue",
            "coordinator",
            "hrs",
            "institution_id",
            "raw_data",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "course_code": {"required": True, "allow_blank": False},
            "start_time": {"required": True, "allow_null": False},
            "end_time": {"required": True, "allow_null": False},
            "venue": {"required": True, "allow_blank": False},
            "hrs": {"required": True, "allow_null": False},
            "institution_id": {"required": True},
            "semester": {"required": True},
        }
