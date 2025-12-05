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