from django.urls import path

from . import views

urlpatterns = [
    path("", views.NoteListCreateView.as_view(), name="note-list"),
    path("study-plans/", views.StudyPlanCreateView.as_view(), name="study-plan-create"),
    path(
        "study-plans/<int:pk>/", views.StudyPlanDetailView.as_view(), name="study-plan-detail"
    ),
    path(
        "study-plans/<int:pk>/regenerate/",
        views.StudyPlanRegenerateView.as_view(),
        name="study-plan-regenerate",
    ),
    path("<int:pk>/", views.NoteDetailView.as_view(), name="note-detail"),
    path("<int:pk>/generate/", views.NoteGenerateView.as_view(), name="note-generate"),
    path("<int:pk>/summary/", views.NoteSummaryView.as_view(), name="note-summary"),
    path("<int:pk>/questions/", views.NoteQuestionsView.as_view(), name="note-questions"),
    path("<int:pk>/podcast/", views.NotePodcastView.as_view(), name="note-podcast"),
    path("jobs/<int:job_id>/", views.JobDetailView.as_view(), name="job-detail"),
]
