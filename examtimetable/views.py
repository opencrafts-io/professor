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

from .models import ExamSchedule
from .serializers import (
    ExamScheduleSerializer,
    ExamScheduleIngestRequestSerializer,
    ExamScheduleIngestItemSerializer
)


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
        course_codes = request.data.get("course_codes")

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

        exams_info = [] # will hold the Data to return

        for course_code in course_codes:
            # removing optional spaces to the search query to match spaces between searches
            course_code = course_code.replace(" ", "")

            if "NUR" in course_code or "NUP" in course_code:
                course_code = course_code[:-1]

            mod_course_code = "".join(f"{char}\s*" for char in course_code)
            for exam_info in ExamSchedule.objects.filter(
                course_code__iregex = f".*{mod_course_code}.*",
            ).all():
                exams_info.append(exam_info)

        serializer = ExamScheduleSerializer(exams_info, many=True)
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


class IngestExamScheduleView(APIView):
    """
    Ingest exam schedules from JSON payload.
    POST: institution_id (required), semester_id (optional), items (required array)
    """

    def post(self, request):
        serializer = ExamScheduleIngestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": "validation_failed",
                    "errors": [
                        {
                            "code": "invalid_request",
                            "message": "The request payload is invalid.",
                            "field_errors": serializer.errors
                        }
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        institution_id = data["institution_id"]
        semester_id = data.get("semester_id")
        items_data = data["items"]

        # 1. Deduplicate within request (last-wins)
        deduplicated_items = {}
        skipped_count = 0
        for i, item_data in enumerate(items_data):
            course_code = item_data["course_code"]
            key = (institution_id, semester_id, course_code)
            if key in deduplicated_items:
                skipped_count += 1
            deduplicated_items[key] = (i, item_data)

        created_count = 0
        updated_count = 0
        errors = []

        # 2. Process items atomically
        try:
            with transaction.atomic():
                for key, (original_index, item_data) in deduplicated_items.items():
                    course_code = item_data["course_code"]

                    lookup = {
                        "course_code": course_code,
                        "institution_id": institution_id,
                        "semester_id": semester_id,
                    }

                    try:
                        obj, created = ExamSchedule.objects.update_or_create(
                            **lookup,
                            defaults=item_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    except Exception as e:
                        errors.append({
                            "code": "server_error",
                            "message": str(e),
                            "item_index": original_index,
                            "key": {
                                "institution_id": institution_id,
                                "semester_id": semester_id,
                                "course_code": course_code
                            }
                        })
                        raise e # Rollback
        except Exception as e:
            # If we didn't populate errors yet, it might be a DB constraint or something else
            if not errors:
                return Response(
                    {
                        "error": "ingestion_failed",
                        "errors": [
                            {
                                "code": "server_error",
                                "message": str(e)
                            }
                        ]
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return Response(
                {
                    "error": "ingestion_failed",
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from event_bus import publisher
            import json

            # Identify unique course codes that were updated
            touched_courses = list(set([item["course_code"] for i, item in deduplicated_items.values()]))

            message = {
                "institution_id": institution_id,
                "semester_id": semester_id,
                "course_codes": touched_courses,
                "timestamp": str(datetime.now())
            }

            publisher.publish(
                exchange="professor.events",
                queue_name="batch.exam_schedule.ingested",
                message=json.dumps(message)
            )
        except Exception as e:
            # Log error but don't fail
            logger.error(f"Failed to publish event: {e}")

        return Response(
            {
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": []
            },
            status=status.HTTP_200_OK
        )
