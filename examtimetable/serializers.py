from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from rest_framework import serializers
from courses.models import SemesterInfo
from zoneinfo import ZoneInfo
import re

from .models import ExamSchedule


class ExamScheduleSerializer(serializers.ModelSerializer):
    # time = serializers.SerializerMethodField()

    class Meta:
        model = ExamSchedule
        fields = [
            "course_code",
            "day",
            "venue",
            "start_time",
            "end_time",
            "campus",
            "coordinator",
            "hrs",
            "invigilator",
            "datetime_str",
        ]


class ExamScheduleIngestItemSerializer(serializers.ModelSerializer):
    """
    Serializer for a single item in the ingestion request.
    Strictly follows the contract fields.
    """
    raw_data = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = ExamSchedule
        fields = [
            "course_code",
            "course_name",
            "exam_date",
            "start_time",
            "end_time",
            "day",
            "venue",
            "campus",
            "coordinator",
            "hrs",
            "invigilator",
            "location",
            "room",
            "building",
            "exam_type",
            "instructions",
            "datetime_str",
            "raw_data",
        ]
        extra_kwargs = {
            "course_code": {"required": True, "allow_blank": False},
        }

    def validate_course_code(self, value):
        return value.strip()

    def to_internal_value(self, data):
        for field in ['start_time', 'end_time']:
            if field in data and isinstance(data[field], str):
                time_str = data[field].replace('.', ':').strip()
                try:
                    # Handle 8:00AM, 08:00 AM, 3:00PM, etc.
                    time_str = time_str.upper().replace(" ", "")
                    parsed_time = datetime.strptime(time_str, "%I:%M%p").time()
                    data[field] = parsed_time.isoformat()
                except ValueError:
                    pass
        return super().to_internal_value(data)


class ExamScheduleIngestRequestSerializer(serializers.Serializer):
    """
    Top-level serializer for the ingestion request.
    """
    institution_id = serializers.CharField(max_length=100, required=True, allow_blank=False)
    semester_id = serializers.IntegerField(required=False, allow_null=True)
    items = ExamScheduleIngestItemSerializer(many=True, required=True)

    def validate_institution_id(self, value):
        return value.strip()

    def create(self, validated_data):
        semester_id = validated_data.pop("semester_id", None)
        if semester_id:
            validated_data["semester"] = SemesterInfo.objects.get(id=semester_id)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        semester_id = validated_data.pop("semester_id", None)
        if semester_id:
            validated_data["semester"] = SemesterInfo.objects.get(id=semester_id)
        return super().update(instance, validated_data)