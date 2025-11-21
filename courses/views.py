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


class StudentCourseEnrollmentView(APIView):
    """
    Enroll student in a course.
    Works for a single course and multiple courses.
    """
    def post(self, request):
        student_id = request.data.get('student_id')
        student_profile_id = request.data.get('student_profile_id')
        semester_id = request.data.get('semester_id')
        course_codes = request.data.get('course_codes', [])

        if not semester_id:
            return Response(
                {"error": "semester_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (student_id or student_profile_id):
            return Response(
                {"error": "student_id or student_profile_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not course_codes:
            return Response(
                {"error": "course_codes is required and must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(course_codes, list):
            return Response(
                {"error": "course_codes must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if student_profile_id:
                student = StudentProfile.objects.get(id=student_profile_id)
            else:
                student = StudentProfile.objects.get(student_id=student_id)

            semester = SemesterInfo.objects.get(id=semester_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except SemesterInfo.DoesNotExist:
            return Response(
                {"error": "Semester not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        courses = Course.objects.filter(course_code__in=course_codes, semester=semester)

        if not courses.exists():
            return Response(
                {"error": "No courses found for the given course_codes in this semester"},
                status=status.HTTP_404_NOT_FOUND
            )

        found_course_codes = set(courses.values_list('course_code', flat=True))
        missing_codes = set(course_codes) - found_course_codes
        if missing_codes:
            return Response(
                {
                    "error": f"Some course codes not found: {list(missing_codes)}",
                    "found_codes": list(found_course_codes),
                    "missing_codes": list(missing_codes)
                },
                status=status.HTTP_404_NOT_FOUND
            )

        created = []
        errors = []

        for course in courses:
            enrollment_data = {
                'student_profile_id': student.id,
                'course_id': course.id,
                'semester_id': semester.id,
                'enrollment_status': request.data.get('enrollment_status', 'enrolled')
            }

            serializer = StudentCourseEnrollmentSerializer(data=enrollment_data)
            if serializer.is_valid():
                try:
                    enrollment = serializer.save()
                    created.append({
                        'course_code': course.course_code,
                        'course_name': course.course_name,
                        'enrollment_id': enrollment.id
                    })
                except Exception as e:
                    errors.append({
                        'course_code': course.course_code,
                        'error': str(e)
                    })
            else:
                errors.append({
                    'course_code': course.course_code,
                    'error': serializer.errors
                })

        response_status = status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST

        return Response({
            'created': created,
            'errors': errors,
            'total_created': len(created),
            'total_errors': len(errors)
        }, status=response_status)


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
