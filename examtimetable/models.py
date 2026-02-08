from django.db import models

from courses.models import SemesterInfo


class ExamSchedule(models.Model):
    course_code = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255, null=True, blank=True)
    semester = models.ForeignKey(SemesterInfo, on_delete=models.CASCADE, related_name='exam_schedule', null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

# Optional fields to support custom formats of timetables.
    day = models.CharField(max_length=50, null=True, blank=True)
    venue = models.CharField(max_length=255, null=True, blank=True)
    campus = models.CharField(max_length=255, null=True, blank=True)
    coordinator = models.CharField(max_length=255, null=True, blank=True)
    hrs = models.CharField(max_length=10, null=True, blank=True)
    invigilator = models.CharField(max_length=255, null=True, blank=True)

    location = models.CharField(max_length=255, null=True, blank=True)
    room = models.CharField(max_length=100, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)

    exam_type = models.CharField(max_length=50, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)

    institution_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['course_code', 'institution_id', 'semester'],
                name='unique_exam_schedule',
                nulls_distinct=False
            )
        ]

    def __str__(self):
        if self.exam_date and self.start_time:
            return f"{self.course_code} - {self.exam_date} {self.start_time}"
        elif self.day:
            return f"{self.course_code} - {self.day}"
        return f"{self.course_code}"

