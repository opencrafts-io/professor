from django.contrib import admin

from .models import Lecturer, StudentCourse


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "student", "institution", "archived_at")


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ("name", "student_course", "email", "phone")
