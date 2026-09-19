from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from professor.pagination import ResultsSetPagination
from users.models import StudentProfile

from .models import Lecturer, SemesterInfo, StudentCourse
from .serializers import LecturerSerializer, SemesterInfoSerializer, StudentCourseSerializer


class StudentCourseCreateView(CreateAPIView):
    serializer_class = StudentCourseSerializer

    def perform_create(self, serializer):
        try:
            student = StudentProfile.objects.get(user=self.request.user)
        except StudentProfile.DoesNotExist:
            raise NotFound("Student profile not found")
        serializer.save(student=student)


class StudentCourseListView(ListAPIView):
    serializer_class = StudentCourseSerializer

    def get_queryset(self):
        try:
            student = StudentProfile.objects.get(user=self.request.user)
        except StudentProfile.DoesNotExist:
            raise NotFound("Student profile not found")
        return StudentCourse.objects.filter(
            student=student, archived_at__isnull=True
        ).order_by("-created_at")


class StudentCourseHistoryView(ListAPIView):
    serializer_class = StudentCourseSerializer

    def get_queryset(self):
        try:
            student = StudentProfile.objects.get(user=self.request.user)
        except StudentProfile.DoesNotExist:
            raise NotFound("Student profile not found")
        return StudentCourse.objects.filter(
            student=student, archived_at__isnull=False
        ).order_by("-created_at")


class StudentCourseDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = StudentCourseSerializer
    lookup_url_kwarg = "id"

    def get_object(self):
        course = get_object_or_404(StudentCourse, pk=self.kwargs["id"])
        if (
            course.student.user_id != self.request.user.user_id
            and not getattr(self.request.user, "is_staff", False)
        ):
            raise PermissionDenied("You don't have permission to manage this course")
        return course


class StudentCourseArchiveView(APIView):
    def post(self, request, id):
        course = get_object_or_404(StudentCourse, pk=id)
        if (
            course.student.user_id != request.user.user_id
            and not getattr(request.user, "is_staff", False)
        ):
            raise PermissionDenied("You don't have permission to manage this course")
        course.archived_at = timezone.now()
        course.save(update_fields=["archived_at"])
        return Response(StudentCourseSerializer(course).data)


class LecturerCreateView(APIView):
    def post(self, request, id):
        course = get_object_or_404(StudentCourse, pk=id)
        if (
            course.student.user_id != request.user.user_id
            and not getattr(request.user, "is_staff", False)
        ):
            raise PermissionDenied("You don't have permission to manage this course")
        serializer = LecturerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lecturer = serializer.save(student_course=course)
        return Response(LecturerSerializer(lecturer).data, status=201)


class LecturerDetailView(APIView):
    def get_object(self):
        lecturer = get_object_or_404(Lecturer, pk=self.kwargs["id"])
        if (
            lecturer.student_course.student.user_id != self.request.user.user_id
            and not getattr(self.request.user, "is_staff", False)
        ):
            raise PermissionDenied("You don't have permission to manage this lecturer")
        return lecturer

    def patch(self, request, id):
        serializer = LecturerSerializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(LecturerSerializer(serializer.save()).data)

    def delete(self, request, id):
        lecturer = self.get_object()
        lecturer.delete()
        return Response(status=204)


class SemesterListView(ListAPIView):
    """List all semesters (paginated)."""

    serializer_class = SemesterInfoSerializer
    queryset = SemesterInfo.objects.all()
    pagination_class = ResultsSetPagination


class SemesterCreateView(CreateAPIView):
    """Create a new semester."""

    serializer_class = SemesterInfoSerializer
    queryset = SemesterInfo.objects.all()


class SemesterDetailView(RetrieveAPIView):
    """Retrieve a specific semester by ID."""

    serializer_class = SemesterInfoSerializer
    queryset = SemesterInfo.objects.all()
    lookup_field = "id"
