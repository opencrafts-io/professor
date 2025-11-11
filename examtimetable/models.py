from django.db import models

from courses.models import SemesterInfo


class ExamSchedule(models.Model):
    course_code = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    semester = models.ForeignKey(SemesterInfo, on_delete=models.CASCADE, related_name='exam_schedule')

    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    location = models.CharField(max_length=255, null=True, blank=True)
    room = models.CharField(max_length=100, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)

    exam_type = models.CharField(max_length=50, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course_code} - {self.exam_date} {self.start_time}"

