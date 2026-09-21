import uuid
from pathlib import Path

from django.db import models
from django.utils import timezone

from courses.models import StudentCourse
from users.models import User


def note_upload_path(instance, filename):
    ext = Path(filename).suffix.lower() or ".pdf"
    return f"notes/{instance.owner.user_id}/{uuid.uuid4().hex}{ext}"


class Note(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    course = models.ForeignKey(
        StudentCourse, on_delete=models.SET_NULL, null=True, blank=True, related_name="notes"
    )
    course_label = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to=note_upload_path)
    original_filename = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.owner.user_id} - {self.original_filename}"


class GenerationJob(models.Model):
    PENDING, PROCESSING, DONE, FAILED = "pending", "processing", "done", "failed"
    STATUS_CHOICES = [(s, s) for s in (PENDING, PROCESSING, DONE, FAILED)]

    # failure_code vocabulary, surfaced verbatim through the job endpoint
    FAILURE_FILE_UNREADABLE = "file_unreadable"
    FAILURE_CONVERSION = "conversion_failed"
    FAILURE_PROVIDER = "llm_provider_error"
    FAILURE_INVALID_OUTPUT = "llm_invalid_output"
    FAILURE_INTERNAL = "internal_error"

    note = models.ForeignKey(
        Note, on_delete=models.CASCADE, null=True, blank=True, related_name="jobs"
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="generation_jobs")
    requested_outputs = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    failure_code = models.CharField(max_length=64, blank=True, default="")
    failure_message = models.TextField(blank=True, default="")
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    prompt_version = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_processing(self):
        self.status = self.PROCESSING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_done(self, *, input_tokens, output_tokens):
        self.status = self.DONE
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "input_tokens", "output_tokens", "finished_at"])

    def mark_failed(self, code, message):
        self.status = self.FAILED
        self.failure_code = code
        self.failure_message = message
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "failure_code", "failure_message", "finished_at"])

    def __str__(self):
        return f"job {self.pk} [{self.status}] outputs={self.requested_outputs}"


class Summary(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="summaries")
    # Artifacts outlive job pruning; the job link is for prompt-quality tracing only.
    job = models.ForeignKey(
        GenerationJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="summaries"
    )
    content = models.JSONField()
    prompt_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"summary {self.pk} for note {self.note_id}"
