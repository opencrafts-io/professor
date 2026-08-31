from django.urls import path

from . import views

urlpatterns = [
    path("", views.NoteListCreateView.as_view(), name="note-list"),
    path("<int:pk>/", views.NoteDetailView.as_view(), name="note-detail"),
]
