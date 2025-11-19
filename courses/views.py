from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Course, StudentCourseEnrollment, SemesterInfo
from .serializers import CourseSerializer, StudentCourseEnrollmentSerializer, SemesterInfoSerializer
from users.models import StudentProfile
from professor.pagination import ResultsSetPagination


class StudentCoursesListView(APIView):
    """
    Get all courses for a specific student.
    Query params: student_id (required)
    """

    def get(self, request):
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response(
                {"error": "student_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        enrollments = StudentCourseEnrollment.objects.filter(student=student)
        serializer = StudentCourseEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CoursesListView(ListAPIView):
    """
    List all courses (paginated).
    Admin endpoint.
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all()
    pagination_class = ResultsSetPagination


class CourseCreateView(CreateAPIView):
    """
    Create a new course.
    Admin endpoint.
    TODO: Confirm permissions involved in this endpoint.
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all()


class CourseDetailView(RetrieveAPIView):
    """
    Retrieve a specific course by ID.
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all()
    lookup_field = 'id'


class SemesterListView(ListAPIView):
    """
    List all semesters (paginated).
    """
    serializer_class = SemesterInfoSerializer
    queryset = SemesterInfo.objects.all()
    pagination_class = ResultsSetPagination


class SemesterCreateView(CreateAPIView):
    """
    Create a new semester.
    """
    serializer_class = SemesterInfoSerializer
    queryset = SemesterInfo.objects.all()


class SemesterDetailView(RetrieveAPIView):
    """
    Retrieve a specific semester by ID.
    """
    serializer_class = SemesterInfoSerializer
    queryset = SemesterInfo.objects.all()
    lookup_field = 'id'
