from django.urls import path

from . import views

urlpatterns = [
    path("", views.NoteListCreateView.as_view(), name="note-list"),
    path("<int:pk>/", views.NoteDetailView.as_view(), name="note-detail"),
    path("<int:pk>/generate/", views.NoteGenerateView.as_view(), name="note-generate"),
    path("<int:pk>/summary/", views.NoteSummaryView.as_view(), name="note-summary"),
    path("jobs/<int:job_id>/", views.JobDetailView.as_view(), name="job-detail"),
]
