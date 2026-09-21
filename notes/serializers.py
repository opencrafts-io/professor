from rest_framework import serializers

from .models import GenerationJob, Note, QuestionSet, Summary


class NoteSerializer(serializers.ModelSerializer):
    course_id = serializers.UUIDField(source="course.pk", allow_null=True, default=None)

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


class GenerationJobSerializer(serializers.ModelSerializer):
    note_id = serializers.IntegerField()
    outputs = serializers.JSONField(source="requested_outputs")
    # empty string in the DB, null on the wire (per contract)
    failure_code = serializers.SerializerMethodField()
    failure_message = serializers.SerializerMethodField()

    class Meta:
        model = GenerationJob
        fields = [
            "id",
            "note_id",
            "outputs",
            "status",
            "failure_code",
            "failure_message",
            "created_at",
            "finished_at",
        ]

    def get_failure_code(self, job):
        return job.failure_code or None

    def get_failure_message(self, job):
        return job.failure_message or None


class SummarySerializer(serializers.ModelSerializer):
    note_id = serializers.IntegerField()
    generated_at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Summary
        fields = ["note_id", "generated_at", "content"]


class QuestionSetSerializer(serializers.ModelSerializer):
    generated_at = serializers.DateTimeField(source="created_at")

    class Meta:
        model = QuestionSet
        fields = ["id", "format", "generated_at", "questions"]
