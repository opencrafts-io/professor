from datetime import datetime
from rest_framework import serializers
from courses.models import SemesterInfo
from .models import ExamSchedule


class ExamScheduleSerializer(serializers.ModelSerializer):
    """
    Standard serializer for outputting exam schedule information.
    """
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


class ExamScheduleIngestItemSerializer(serializers.ModelSerializer):
    """
    Serializer for a single item in the ingestion request.
    Expects fully processed, strict information.
    """
    raw_data = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = ExamSchedule
        fields = [
            "course_code",
            "start_time",
            "end_time",
            "venue",
            "coordinator",
            "hrs",
            "raw_data",
        ]
        extra_kwargs = {
            "course_code": {"required": True, "allow_blank": False},
            "start_time": {"required": True, "allow_null": False},
            "end_time": {"required": True, "allow_null": False},
            "venue": {"required": True, "allow_blank": False},
        }


class ExamScheduleIngestRequestSerializer(serializers.Serializer):
    """
    Top-level serializer for the ingestion request.
    """
    institution_id = serializers.CharField(max_length=100, required=True)
    semester_id = serializers.IntegerField(required=False, allow_null=True)
    items = ExamScheduleIngestItemSerializer(many=True, required=True)

