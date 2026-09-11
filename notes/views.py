from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from courses.models import Course
from professor.pagination import ResultsSetPagination

from .errors import APIError, ErrorCode, NotesAPIView
from .llm.base import OutputType
from .models import GenerationJob, Note
from .serializers import NoteSerializer
from .services.entitlements import HasAIEntitlement
from .tasks import run_generation

# generation grows to questions (wk4) and podcast (wk5)
IMPLEMENTED_OUTPUTS = {OutputType.SUMMARY.value}


def get_owned_note(request, pk):
    note = Note.objects.filter(pk=pk, owner=request.user).first()
    if note is None:
        raise APIError("Note not found.", code=ErrorCode.NOT_FOUND, status_code=404)
    return note


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


class NoteDetailView(NotesAPIView):
    permission_classes = [HasAIEntitlement]

    def get(self, request, pk):
        note = get_owned_note(request, pk)
        data = NoteSerializer(note).data
        data["artifacts"] = {
            "summary": False,
            "questions": [],
            "podcast": False,
            "study_plans": [],
        }
        return Response(data)

    def delete(self, request, pk):
        note = get_owned_note(request, pk)
        try:
            note.file.delete(save=False)
        except FileNotFoundError:
            pass  # missing blob on delete is the desired end state
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteGenerateView(NotesAPIView):
    permission_classes = [HasAIEntitlement]

    def post(self, request, pk):
        note = get_owned_note(request, pk)
        outputs = request.data.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            raise APIError(
                "'outputs' must be a non-empty list.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )
        unsupported = [o for o in outputs if o not in IMPLEMENTED_OUTPUTS]
        if unsupported:
            raise APIError(
                "Unsupported output types requested.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"unsupported": unsupported, "supported": sorted(IMPLEMENTED_OUTPUTS)},
            )
        in_flight = note.jobs.filter(
            status__in=[GenerationJob.PENDING, GenerationJob.PROCESSING]
        ).exists()
        if in_flight:
            raise APIError(
                "A generation job for this note is already running.",
                code=ErrorCode.JOB_ALREADY_RUNNING,
                status_code=409,
            )
        job = GenerationJob.objects.create(note=note, owner=request.user, requested_outputs=outputs)
        run_generation.delay(job.pk)
        return Response({"job_id": job.pk}, status=status.HTTP_202_ACCEPTED)
