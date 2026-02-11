from django.urls import path
from . import views

urlpatterns = [
    path('student/', views.StudentExamScheduleView.as_view(), name='student-exam-schedule'),
    path('ingest/', views.IngestExamScheduleView.as_view(), name='ingest-exam-schedule'),
    path('by-codes/', views.ExamScheduleByCourseCodesView.as_view(), name='exam-schedule-by-codes'),
    path('by-institution/', views.ExamScheduleByInstitutionView.as_view(), name='exam-schedule-by-institution'),
    path('', views.ExamScheduleListView.as_view(), name='exam-schedule-list'),
]

