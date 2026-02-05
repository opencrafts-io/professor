from users.models import StudentProfile
from institutions.models import Institution
from django.db import models


class SemesterInfo(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    course_code = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    semester = models.ForeignKey(
        SemesterInfo, on_delete=models.CASCADE, related_name="courses"
    )

    course_id = models.CharField(max_length=100, null=True, blank=True)
    instructor = models.CharField(max_length=255, null=True, blank=True)
    credits = models.FloatField(null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)

    meeting_times = models.JSONField(default=list, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    enrollment_status = models.CharField(max_length=50, null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='courses', null=True, blank=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class Grade(models.Model):
    GRADE_SCALE_CHOICES = [
        ("letter", "Letter"),
        ("gpa_4", "GPA 4.0"),
        ("gpa_5", "GPA 5.0"),
        ("percentage", "Percentage"),
        ("pass_fail", "Pass/Fail"),
    ]

    course_code = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    semester = models.ForeignKey(SemesterInfo, on_delete=models.CASCADE)
    grade = models.CharField(max_length=50)

    grade_points = models.FloatField(null=True, blank=True)
    credits = models.FloatField(null=True, blank=True)
    grade_scale = models.CharField(
        max_length=20, choices=GRADE_SCALE_CHOICES, null=True
    )

    instructor = models.CharField(max_length=255, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.course_code} - {self.grade}"


class ScheduleEntry(models.Model):
    DAY_CHOICES = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    course_code = models.CharField(max_length=50)
    course_name = models.CharField(max_length=255)
    day_of_week = models.CharField(max_length=9, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    location = models.CharField(max_length=255, null=True, blank=True)
    room = models.CharField(max_length=100, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)
    instructor = models.CharField(max_length=255, null=True, blank=True)

    is_recurring = models.BooleanField(default=True)
    recurrence_pattern = models.CharField(max_length=50, null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course_code} - {self.day_of_week} {self.start_time}"

class Transcript(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='transcripts')

    overall_gpa = models.FloatField(null=True, blank=True)
    total_credits = models.FloatField(null=True, blank=True)

    awards = models.JSONField(default=list, blank=True)
    academic_standing = models.CharField(max_length=100, null=True, blank=True)
    generated_date = models.DateField(null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.student.program} - {self.generated_date}"

class StudentCourseEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='student_course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_course_enrollments')
    semester = models.ForeignKey(SemesterInfo, on_delete=models.CASCADE, related_name='student_course_enrollments')
    enrollment_status = models.CharField(max_length=50, default='enrolled', null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'course', 'semester']

    def __str__(self):
        return f"{self.student.user.username} - {self.course.course_code} - {self.semester.code}"