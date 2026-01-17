import uuid

from django.db import models

from institutions.models import Institution


class User(models.Model):
    user_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
    )
    name = models.CharField(max_length=512)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    username = models.CharField(max_length=100, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    vibe_points = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
        ]

    def __str__(self):
        """
        Provide a concise display string identifying the user by username and name.

        Returns:
            str: A string formatted as "@{username} - ({name})".
        """
        return f"@{self.username} - ({self.name})"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=100, unique=True)
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True
    )

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
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="administrator"
    )
    institution_name = models.CharField(max_length=255)
    institution_code = models.CharField(max_length=100)  # unique=True

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.institution_name})"


class Credentials(models.Model):
    """
    Stores a user's institutional login credentials.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="credentials"
    )
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)

    additional_fields = models.JSONField(default=dict, blank=True)

    mfa_code = models.CharField(max_length=10, null=True, blank=True)

    mfa_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    oauth_token = models.TextField(null=True, blank=True)
    oauth_state = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.username

