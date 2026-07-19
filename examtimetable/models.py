from django.db import models

from courses.models import SemesterInfo
from institutions.models import Institution


class ExamSchedule(models.Model):
    course_code = models.CharField(max_length=50)
    semester = models.ForeignKey(
        SemesterInfo,
        on_delete=models.CASCADE,
        related_name="exam_schedule",
        null=True,
        blank=True,
    )
    start_time = models.DateTimeField(null=False)
    end_time = models.DateTimeField(null=False)
    venue = models.CharField(max_length=255, null=False)
    coordinator = models.CharField(max_length=255, null=True, blank=True)
    hrs = models.CharField(max_length=10, null=False)
    institution_id = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="institution"
    )

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course_code", "institution_id", "semester"],
                name="unique_exam_schedule",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["institution_id", "semester", "course_code"]),
        ]

    def __str__(self):
        return f"{self.course_code} - {self.start_time}"
