import uuid

from django.db import models

from courses.models import Course
from users.models import User


def note_upload_path(instance, filename):
    return f"notes/{instance.owner.user_id}/{uuid.uuid4().hex}.pdf"


class Note(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="notes"
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
