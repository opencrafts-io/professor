from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLES, default='student')
    institution_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_administrator(self):
        return self.role == 'admin'

class StudentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=100, unique=True)

    national_id = models.CharField(max_length=100, null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)

    program = models.CharField(max_length=255, null=True, blank=True)
    major = models.CharField(max_length=255, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    gpa = models.FloatField(null=True, blank=True)

    disability_status = models.CharField(max_length=100, null=True, blank=True)
    school = models.CharField(max_length=255, null=True, blank=True)

    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    enrollment_date = models.DateField(null=True, blank=True)
    expected_graduation = models.DateField(null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.student_id})"


class Administrator(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="administrator")
    institution_name = models.CharField(max_length=255)
    institution_code = models.CharField(max_length=100) # unique=True

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.institution_name})"
