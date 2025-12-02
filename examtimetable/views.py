from datetime import datetime
from django.db.models import QuerySet
from courses.models import SemesterInfo, StudentCourseEnrollment
from django.db import transaction
from professor.pagination import ResultsSetPagination
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import StudentProfile

from .helpers import (
    kca_extractor,
    nursing_exam_timetable_parser,
    parse_school_exam_timetable,
    strath_extractor,
)
from .models import ExamSchedule
from .serializers import ExamScheduleSerializer


class StudentExamScheduleView(APIView):
    """
    Get exam schedule for a specific student based on their enrolled courses.
    Query params: student_id (required), semester_id (optional)
    """

    def get(self, request):
        student_id = request.query_params.get("student_id")
        semester_id = request.query_params.get("semester_id")

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
        if semester_id:
            try:
                semester = SemesterInfo.objects.get(id=semester_id)
                enrollments = enrollments.filter(semester=semester)
            except SemesterInfo.DoesNotExist:
                return Response(
                    {"error": "Semester not found"}, status=status.HTTP_404_NOT_FOUND
                )

        course_codes = [enrollment.course.course_code for enrollment in enrollments]

        exams = ExamSchedule.objects.filter(course_code__in=course_codes)
        if semester_id:
            exams = exams.filter(semester_id=semester_id)

        serializer = ExamScheduleSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ParseExamTimetableView(APIView):
    """
    Parse and upload exam timetable from Excel file.
    POST: file (Excel file), file_name (parser type: 'school_exams', 'nursing_exams', 'strath', 'kca')
    """

    def post(self, request):
        file = request.FILES.get("file")
        file_name = request.data.get("file_name")
        semester_id = request.data.get("semester_id")
        institution_id = request.data.get("institution_id")

        if not file:
            return Response(
                {"error": "file is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not file_name:
            return Response(
                {
                    "error": "file_name is required. Options: 'school_exams', 'nursing_exams', 'strath', 'kca'"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        semester = None
        if semester_id:
            try:
                semester = SemesterInfo.objects.get(id=semester_id)
            except SemesterInfo.DoesNotExist:
                return Response(
                    {"error": "Semester not found"}, status=status.HTTP_404_NOT_FOUND
                )

        try:
            if file_name == "school_exams":
                courses = parse_school_exam_timetable(file)
            elif file_name == "nursing_exams":
                courses = nursing_exam_timetable_parser(file)
            elif file_name == "strath":
                courses = strath_extractor(file)
            elif file_name == "kca":
                courses = kca_extractor(file)
            else:
                return Response(
                    {
                        "error": f"Unknown file_name: {file_name}. Options: 'school_exams', 'nursing_exams', 'strath', 'kca'"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"error": f"Error parsing file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for course_data in courses:
                course_code = course_data.get("course_code", "").strip()
                if not course_code:
                    continue

                if len(course_code) > 50:
                    continue

                invalid_keywords = [
                    "UNIVERSITY",
                    "BACHELOR",
                    "SCHOOL",
                    "INSTITUTE",
                    "DEPARTMENT",
                    "FACULTY",
                    "COLLEGE",
                    "PROGRAMME",
                    "PROGRAM",
                ]
                if any(keyword in course_code.upper() for keyword in invalid_keywords):
                    continue

                course_name = course_data.get("course_name", course_code)
                if course_name and len(course_name) > 255:
                    course_name = course_name[:255]

                exam_date = None
                start_time = None
                end_time = None

                if course_data.get("day"):
                    day_str = course_data["day"]
                    if " " in day_str:
                        try:
                            date_part = day_str.split(" ", 1)[1]
                            exam_date = datetime.strptime(date_part, "%d/%m/%y").date()
                        except (ValueError, IndexError):
                            pass

                if course_data.get("time"):
                    time_str = course_data["time"]
                    if "-" in time_str:
                        try:
                            start_str, end_str = time_str.split("-", 1)
                            start_str = start_str.strip()
                            end_str = end_str.strip()

                            formats = ["%I:%M%p", "%H:%M", "%I:%M %p", "%H:%M "]
                            start_time = None
                            end_time = None

                            for fmt in formats:
                                try:
                                    start_time = datetime.strptime(
                                        start_str, fmt
                                    ).time()
                                    break
                                except ValueError:
                                    continue

                            for fmt in formats:
                                try:
                                    end_time = datetime.strptime(end_str, fmt).time()
                                    break
                                except ValueError:
                                    continue
                        except (ValueError, IndexError):
                            pass

                exam_data = {
                    "course_code": course_code,
                    "course_name": course_name if course_name else course_code,
                    "day": course_data.get("day", ""),
                    "venue": course_data.get("venue", ""),
                    "campus": course_data.get("campus", ""),
                    "coordinator": course_data.get("coordinator", ""),
                    "hrs": course_data.get("hrs", ""),
                    "invigilator": course_data.get("invigilator", ""),
                    "location": course_data.get(
                        "venue", course_data.get("location", "")
                    ),
                    "raw_data": course_data,
                }

                if exam_date:
                    exam_data["exam_date"] = exam_date
                if start_time:
                    exam_data["start_time"] = start_time
                if end_time:
                    exam_data["end_time"] = end_time

                if semester:
                    exam_data["semester_id"] = semester.pk
                if institution_id:
                    exam_data["institution_id"] = institution_id

                serializer = ExamScheduleSerializer(data=exam_data)
                if serializer.is_valid():
                    lookup = {
                        "course_code": course_code,
                        "semester": semester if semester else None,
                    }
                    if institution_id:
                        lookup["institution_id"] = institution_id

                    exam_schedule, created = ExamSchedule.objects.update_or_create(
                        **lookup,
                        defaults=serializer.validated_data,
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                else:
                    # duplicate course, we handle by deleting duplicate courses
                    if serializer.errors.get('course_code')[0] == \
                        "exam schedule with this course code already exists.":
                        dup_course = ExamSchedule.objects.get(
                            course_code=course_code,
                        )
                        dup_course.delete()
                        continue
                    return Response(
                        {
                            "error": f"Validation error for course {course_code}: {serializer.errors}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        return Response(
            {
                "message": "Successfully parsed and saved exam timetable",
                "created": created_count,
                "updated": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class ExamScheduleListView(ListAPIView):
    """
    List all exam schedules (paginated).
    Query params: course_code (optional), semester_id (optional)
    """

    serializer_class = ExamScheduleSerializer
    pagination_class = ResultsSetPagination

    def get_queryset(self) -> QuerySet[ExamSchedule]:
        queryset = ExamSchedule.objects.all()
        course_code = self.request.query_params.get("course_code")
        semester_id = self.request.query_params.get("semester_id")

        if course_code:
            queryset = queryset.filter(course_code__icontains=course_code)
        if semester_id:
            queryset = queryset.filter(semester_id=semester_id)

        return queryset


class ExamScheduleByCourseCodesView(APIView):
    """
    Get exam schedules for a list of course codes.
    """

    def post(self, request):
        institution_id = request.data.get("institution_id")
        course_codes = request.data.get("course_codes", [])

        if not institution_id:
            return Response(
                {"error": "institution_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not course_codes or not isinstance(course_codes, list):
            return Response(
                {"error": "course_codes must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        exams = ExamSchedule.objects.filter(
            institution_id=institution_id, course_code__in=course_codes
        )
        serializer = ExamScheduleSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExamScheduleByInstitutionView(APIView):
    """
    Get exam schedules for a specific institution.
    Query params: institution_id (required), semester_id (optional)
    """

    def get(self, request):
        institution_id = request.query_params.get("institution_id")
        semester_id = request.query_params.get("semester_id")

        if not institution_id:
            return Response(
                {"error": "institution_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        exams = ExamSchedule.objects.filter(institution_id=institution_id)

        if semester_id:
            exams = exams.filter(semester_id=semester_id)

        serializer = ExamScheduleSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
