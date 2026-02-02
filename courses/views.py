from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from institutions.models import Institution
from professor.pagination import ResultsSetPagination
from users.models import StudentProfile

from .models import Course, SemesterInfo, StudentCourseEnrollment
from .serializers import (
    CourseRegistrationSerializer,
    CourseSerializer,
    SemesterInfoSerializer,
    StudentCourseEnrollmentSerializer,
)


class StudentCoursesListView(APIView):
    """
    Get all courses for a specific student.
    Query params: student_id (required)
    """

    def get(self, request):
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND
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
        student_id = request.data.get("student_id")
        student_profile_id = request.data.get("student_profile_id")
        semester_id = request.data.get("semester_id")
        course_codes = request.data.get("course_codes", [])

        if not semester_id:
            return Response(
                {"error": "semester_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not (student_id or student_profile_id):
            return Response(
                {"error": "student_id or student_profile_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not course_codes:
            return Response(
                {"error": "course_codes is required and must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(course_codes, list):
            return Response(
                {"error": "course_codes must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if student_profile_id:
                student = StudentProfile.objects.get(id=student_profile_id)
            else:
                student = StudentProfile.objects.get(student_id=student_id)

            semester = SemesterInfo.objects.get(id=semester_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except SemesterInfo.DoesNotExist:
            return Response(
                {"error": "Semester not found"}, status=status.HTTP_404_NOT_FOUND
            )

        courses = Course.objects.filter(course_code__in=course_codes, semester=semester)

        if not courses.exists():
            return Response(
                {
                    "error": "No courses found for the given course_codes in this semester"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        found_course_codes = set(courses.values_list("course_code", flat=True))
        missing_codes = set(course_codes) - found_course_codes
        if missing_codes:
            return Response(
                {
                    "error": f"Some course codes not found: {list(missing_codes)}",
                    "found_codes": list(found_course_codes),
                    "missing_codes": list(missing_codes),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        created = []
        errors = []

        for course in courses:
            enrollment_data = {
                "student_profile_id": student.id,
                "course_id": course.id,
                "semester_id": semester.id,
                "enrollment_status": request.data.get("enrollment_status", "enrolled"),
            }

            serializer = StudentCourseEnrollmentSerializer(data=enrollment_data)
            if serializer.is_valid():
                try:
                    enrollment = serializer.save()
                    created.append(
                        {
                            "course_code": course.course_code,
                            "course_name": course.course_name,
                            "enrollment_id": enrollment.id,
                        }
                    )
                except Exception as e:
                    errors.append({"course_code": course.course_code, "error": str(e)})
            else:
                errors.append(
                    {"course_code": course.course_code, "error": serializer.errors}
                )

        response_status = (
            status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST
        )

        return Response(
            {
                "created": created,
                "errors": errors,
                "total_created": len(created),
                "total_errors": len(errors),
            },
            status=response_status,
        )


class CourseRegistrationView(APIView):
    """
    Register a course and enroll a student.
    """

    def post(self, request):
        serializer = CourseRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Extract fields
        course_code = data["course_code"]
        semester_code = data["semester"]
        institution_id = data["institution"]
        student_id = data["student_id"]

        # Verify Institution
        try:
            institution = Institution.objects.get(institution_id=institution_id)
        except Institution.DoesNotExist:
            return Response(
                {"error": "Institution not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify Semester or create based on current time
        import calendar
        from datetime import date

        # Helper to get current semester info
        today = date.today()
        year = today.year
        month = today.month

        if 1 <= month <= 4:
            current_intake = "Jan"
            start_month = 1
            end_month = 4
        elif 5 <= month <= 8:
            current_intake = "May"
            start_month = 5
            end_month = 8
        else:
            current_intake = "Sep"
            start_month = 9
            end_month = 12

        current_sem_code = f"{current_intake}{year}"
        current_sem_name = f"{current_intake} {year}"
        current_start_date = date(year, start_month, 1)
        # End date approx
        if end_month == 12:
            current_end_date = date(year, 12, 31)
        else:
            last_day = calendar.monthrange(year, end_month)[1]
            current_end_date = date(year, end_month, last_day)

        target_semester = None

        if semester_code == current_sem_code:
            target_semester, _ = SemesterInfo.objects.get_or_create(
                code=current_sem_code,
                defaults={
                    "name": current_sem_name,
                    "start_date": current_start_date,
                    "end_date": current_end_date,
                    "year": year,
                    "is_current": True,
                },
            )
        else:
            try:
                target_semester = SemesterInfo.objects.get(code=semester_code)
            except SemesterInfo.DoesNotExist:
                return Response(
                    {
                        "error": f"Semester {semester_code} not found and does not match current intake {current_sem_code}"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        semester = target_semester

        course, created = Course.objects.get_or_create(
            course_code=course_code,
            semester=semester,
            institution=institution,
            defaults={
                "course_name": data.get("course_name"),
                "course_id": data.get("course_id"),
                "instructor": data.get("instructor"),
                "credits": data.get("credits"),
                "department": data.get("department"),
                "meeting_times": data.get("meeting_times"),
                "location": data.get("campus"),
                "raw_data": data,  # Store extra fields if any
            },
        )

        if not created:
            course.course_name = data.get("course_name", course.course_name)
            course.course_id = data.get("course_id", course.course_id)
            course.instructor = data.get("instructor", course.instructor)
            course.credits = data.get("credits", course.credits)
            course.department = data.get("department", course.department)
            course.meeting_times = data.get("meeting_times", course.meeting_times)
            course.location = data.get("campus", course.location)
            course.save()

        # Enroll Student
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND
            )

        enrollment, enrolled = StudentCourseEnrollment.objects.get_or_create(
            student=student,
            course=course,
            semester=semester,
            defaults={"enrollment_status": "enrolled"},
        )

        return Response(
            {
                "course": {
                    "course_code": course.course_code,
                    "course_name": course.course_name,
                    "id": course.course_id,
                },
                "enrollment": {
                    "status": enrollment.enrollment_status,
                    "enrolled": enrolled,
                },
            },
            status=status.HTTP_201_CREATED,
        )


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
    lookup_field = "id"


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
    lookup_field = "id"
