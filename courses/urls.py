from django.urls import path

from . import views


urlpatterns = [
    path("create/", views.StudentCourseCreateView.as_view(), name="course-create"),
    path("student/", views.StudentCourseListView.as_view(), name="student-courses"),
    path(
        "student/history/",
        views.StudentCourseHistoryView.as_view(),
        name="student-course-history",
    ),
    path("<uuid:id>/", views.StudentCourseDetailView.as_view(), name="course-detail"),
    path(
        "<uuid:id>/archive/",
        views.StudentCourseArchiveView.as_view(),
        name="course-archive",
    ),
    path(
        "<uuid:id>/lecturers/",
        views.LecturerCreateView.as_view(),
        name="lecturer-create",
    ),
    path(
        "lecturers/<uuid:id>/",
        views.LecturerDetailView.as_view(),
        name="lecturer-detail",
    ),
    path("semesters/", views.SemesterListView.as_view(), name="semester-list"),
    path("semesters/create/", views.SemesterCreateView.as_view(), name="semester-create"),
    path(
        "semesters/<int:id>/", views.SemesterDetailView.as_view(), name="semester-detail"
    ),
]
