from django.contrib import admin

from .models import Lecturer, ScheduleEntry, StudentCourse


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "student", "institution", "archived_at")


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ("name", "student_course", "email", "phone")


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = (
        "student_course",
        "day_of_week",
        "start_time",
        "end_time",
        "label",
        "venue",
    )
