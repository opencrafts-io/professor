from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from courses.models import SemesterInfo
from zoneinfo import ZoneInfo
import re

from .models import ExamSchedule


class ExamScheduleSerializer(serializers.ModelSerializer):
    semester_id = serializers.IntegerField(write_only=True, required=False)
    # time = serializers.SerializerMethodField()
    datetime_str = serializers.SerializerMethodField()

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
            "semester_id",
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
            "raw_data",
        ]
        extra_kwargs = {
            "course_code": {"required": True, "allow_blank": False},
        }

    def validate_course_code(self, value):
        return value.strip()


class ExamScheduleIngestRequestSerializer(serializers.Serializer):
    """
    Top-level serializer for the ingestion request.
    """
    institution_id = serializers.CharField(max_length=100, required=True, allow_blank=False)
    semester_id = serializers.IntegerField(required=False, allow_null=True)
    items = ExamScheduleIngestItemSerializer(many=True, required=True)

    def validate_institution_id(self, value):
        return value.strip()

    # currently only handles daystar exams will change to handle KCA
    # this functionality should be moved to the parsers
    def get_datetime_str(self, instance):
        """
        returns Iso format
        """
        pattern = r"^\d{2}/\d{2}/\d{4}$"
        crs_date = instance.day.split()[1]
        date_str = crs_date + " " + str(instance.start_time)
        if re.match(pattern, crs_date):
            naive_dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
        else:
            naive_dt = datetime.strptime(date_str, "%d/%m/%y %H:%M:%S")

        aware_dt = naive_dt.replace(tzinfo=ZoneInfo("Africa/Nairobi"))

        return aware_dt.isoformat()

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