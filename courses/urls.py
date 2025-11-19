from django.urls import path
from . import views

urlpatterns = [
    path('student/', views.StudentCoursesListView.as_view(), name='student-courses'),
    path('', views.CoursesListView.as_view(), name='courses-list'),
    path('create/', views.CourseCreateView.as_view(), name='course-create'),
    path('<int:id>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('semesters/', views.SemesterListView.as_view(), name='semester-list'),
    path('semesters/create/', views.SemesterCreateView.as_view(), name='semester-create'),
    path('semesters/<int:id>/', views.SemesterDetailView.as_view(), name='semester-detail'),
]

