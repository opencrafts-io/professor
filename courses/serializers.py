from rest_framework import serializers

from .models import Lecturer, SemesterInfo, StudentCourse


class SemesterInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SemesterInfo
        fields = "__all__"


class StudentCourseSerializer(serializers.ModelSerializer):
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


class LecturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecturer
        fields = "__all__"
        read_only_fields = ["id", "student_course"]
