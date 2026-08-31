from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from courses.models import Course
from professor.pagination import ResultsSetPagination

from .errors import APIError, ErrorCode, NotesAPIView
from .models import Note
from .serializers import NoteSerializer
from .services.entitlements import HasAIEntitlement


class NoteListCreateView(NotesAPIView):
    permission_classes = [HasAIEntitlement]

    def get(self, request):
        queryset = Note.objects.filter(owner=request.user)
        paginator = ResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(NoteSerializer(page, many=True).data)

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise APIError(
                "A PDF file is required.", code=ErrorCode.VALIDATION_ERROR, status_code=400
            )
        head = upload.read(5)
        upload.seek(0)
        if head != b"%PDF-":
            raise APIError(
                "Only PDF files are accepted.", code=ErrorCode.NOTE_NOT_PDF, status_code=400
            )
        max_bytes = settings.NOTES_MAX_UPLOAD_BYTES
        if upload.size > max_bytes:
            raise APIError(
                "File exceeds the maximum allowed size.",
                code=ErrorCode.FILE_TOO_LARGE,
                status_code=400,
                details={"max_bytes": max_bytes},
            )

        course = None
        course_id = request.data.get("course_id")
        if course_id:
            course = Course.objects.filter(pk=course_id).first()
            if course is None:
                raise APIError(
                    "Unknown course_id.",
                    code=ErrorCode.VALIDATION_ERROR,
                    status_code=400,
                    details={"course_id": course_id},
                )

        note = Note.objects.create(
            owner=request.user,
            course=course,
            course_label=request.data.get("course_label", ""),
            file=upload,
            original_filename=upload.name,
            size_bytes=upload.size,
        )
        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)
