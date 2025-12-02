from datetime import datetime

from rest_framework import serializers

from courses.models import SemesterInfo
from .models import ExamSchedule


class ExamScheduleSerializer(serializers.ModelSerializer):
    semester_id = serializers.IntegerField(write_only=True, required=False)
    time = serializers.SerializerMethodField()
    datetime_str = serializers.SerializerMethodField()

    class Meta:
        model = ExamSchedule
        fields = [
            "course_code",
            "day",
            "time",
            "venue",
            "campus",
            "coordinator",
            "hrs",
            "invigilator",
            "datetime_str",
            "semester_id",
        ]
        read_only_fields = [
            "course_code",
            "day",
            "time",
            "venue",
            "campus",
            "coordinator",
            "hrs",
            "invigilator",
            "datetime_str",
        ]

    def get_time(self, obj):
        if obj.raw_data and "time" in obj.raw_data:
            return obj.raw_data["time"]

        if obj.start_time and obj.end_time:
            start_str = obj.start_time.strftime("%I:%M%p").lstrip("0")
            end_str = obj.end_time.strftime("%I:%M%p").lstrip("0")
            return f"{start_str}-{end_str}"

        return ""

    def get_datetime_str(self, obj):
        if obj.exam_date and obj.start_time:
            dt = datetime.combine(obj.exam_date, obj.start_time)
            return dt.isoformat()

        # Fallback: try to derive from raw_data (day + time) like wookie
        raw = obj.raw_data or {}
        day_str = raw.get("day") or obj.day or ""
        time_str = raw.get("time") or ""

        if day_str and time_str:
            try:
                parts = day_str.split()
                if len(parts) >= 2:
                    date_part = parts[1]
                    date_val = datetime.strptime(date_part, "%d/%m/%y").date()
                else:
                    date_val = datetime.strptime(day_str, "%Y-%m-%d").date()

                start_part = time_str.split("-", 1)[0].strip()

                for fmt in ["%I:%M%p", "%I:%M %p", "%H:%M", "%H.%M"]:
                    try:
                        t_val = datetime.strptime(start_part, fmt).time()
                        break
                    except ValueError:
                        t_val = None
                if t_val:
                    return datetime.combine(date_val, t_val).isoformat()
            except Exception:
                pass

        return None

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