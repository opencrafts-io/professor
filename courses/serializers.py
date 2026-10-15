import re

from rest_framework import serializers

from .models import Lecturer, ScheduleEntry, SemesterInfo, StudentCourse


HEX_COLOR_PATTERN = re.compile(r"^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def validate_hex_color(value):
    if value and not HEX_COLOR_PATTERN.fullmatch(value):
        raise serializers.ValidationError(
            "Color must be a 6- or 8-digit hexadecimal value."
        )
    return value


class SemesterInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SemesterInfo
        fields = "__all__"


class LecturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecturer
        fields = "__all__"
        read_only_fields = ["id", "student_course"]


class ScheduleEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleEntry
        fields = "__all__"
        read_only_fields = ["id", "student_course", "created_at", "updated_at"]
        extra_kwargs = {"idempotency_key": {"write_only": True}}

    def validate_color(self, value):
        return validate_hex_color(value)

    def validate(self, attrs):
        start_time = attrs.get(
            "start_time", getattr(self.instance, "start_time", None)
        )
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time is not None and end_time is not None and start_time >= end_time:
            raise serializers.ValidationError("start_time must be before end_time.")

        is_recurring = attrs.get(
            "is_recurring", getattr(self.instance, "is_recurring", True)
        )
        specific_date = attrs.get(
            "specific_date", getattr(self.instance, "specific_date", None)
        )
        if is_recurring and specific_date is not None:
            raise serializers.ValidationError(
                "specific_date must be empty for a recurring schedule entry."
            )
        if not is_recurring and specific_date is None:
            raise serializers.ValidationError(
                "specific_date is required for a non-recurring schedule entry."
            )
        return attrs


class StudentCourseSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCourse
        fields = ["id", "title", "code", "color"]


class StudentTimetableEntrySerializer(ScheduleEntrySerializer):
    course = StudentCourseSummarySerializer(source="student_course", read_only=True)

    class Meta(ScheduleEntrySerializer.Meta):
        fields = [
            "id",
            "day_of_week",
            "start_time",
            "end_time",
            "venue",
            "campus",
            "section",
            "label",
            "color",
            "is_recurring",
            "specific_date",
            "created_at",
            "updated_at",
            "course",
        ]
        read_only_fields = fields


class StudentCourseSerializer(serializers.ModelSerializer):
    lecturers = LecturerSerializer(many=True, read_only=True)
    schedule_entries = ScheduleEntrySerializer(many=True, read_only=True)

    class Meta:
        model = StudentCourse
        fields = "__all__"
        read_only_fields = [
            "id",
            "student",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"idempotency_key": {"write_only": True}}

    def validate_color(self, value):
        return validate_hex_color(value)

    def validate_previous_course(self, value):
        request = self.context["request"]
        if (
            value is not None
            and value.student.user_id != request.user.user_id
            and not getattr(request.user, "is_staff", False)
        ):
            raise serializers.ValidationError(
                "Previous course must belong to the authenticated student."
            )
        return value
