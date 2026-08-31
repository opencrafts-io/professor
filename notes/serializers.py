from rest_framework import serializers

from .models import Note


class NoteSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source="course.pk", allow_null=True, default=None)

    class Meta:
        model = Note
        fields = [
            "id",
            "course_id",
            "course_label",
            "original_filename",
            "size_bytes",
            "uploaded_at",
        ]
