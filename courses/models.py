import uuid

from django.db import models

from institutions.models import Institution
from users.models import StudentProfile


class SemesterInfo(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class StudentCourse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT)
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    term_label = models.CharField(max_length=100, blank=True, null=True)
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    term_start_date = models.DateField(blank=True, null=True)
    term_end_date = models.DateField(blank=True, null=True)
    previous_course = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="next_attempts",
    )
    archived_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "archived_at"]),
            models.Index(fields=["institution"]),
        ]


class Lecturer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_course = models.ForeignKey(
        StudentCourse, on_delete=models.CASCADE, related_name="lecturers"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    office = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["student_course"])]
