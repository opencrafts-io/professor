from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from courses.models import StudentCourse
from professor.pagination import ResultsSetPagination

from .errors import APIError, ErrorCode, NotesAPIView
from .llm.base import QUESTION_FORMATS, OutputType
from .models import GenerationJob, Note
from .serializers import (
    GenerationJobSerializer,
    NoteSerializer,
    QuestionSetSerializer,
    SummarySerializer,
)
from .services.entitlements import HasAIEntitlement
from .tasks import run_generation

# generation grows to podcast (wk5) and study plans (wk6)
IMPLEMENTED_OUTPUTS = {OutputType.SUMMARY.value, OutputType.QUESTIONS.value}


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

    # extension -> required magic bytes (Office Open XML files are ZIP containers).
    SUPPORTED_TYPES = {
        ".pdf": b"%PDF-",
        ".docx": b"PK\x03\x04",
        ".pptx": b"PK\x03\x04",
        ".xlsx": b"PK\x03\x04",
        ".xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    }

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise APIError(
                "A file upload is required.", code=ErrorCode.VALIDATION_ERROR, status_code=400
            )
        ext = Path(upload.name).suffix.lower()
        magic = self.SUPPORTED_TYPES.get(ext)
        head = upload.read(max(len(signature) for signature in self.SUPPORTED_TYPES.values()))
        upload.seek(0)
        if magic is None or not head.startswith(magic):
            raise APIError(
                "Only PDF, Word (.docx), PowerPoint (.pptx), and Excel (.xlsx/.xls) files are accepted.",
                code=ErrorCode.UNSUPPORTED_FILE_TYPE,
                status_code=400,
                details={"supported": sorted(self.SUPPORTED_TYPES)},
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
            course = StudentCourse.objects.filter(pk=course_id).first()
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
            "summary": note.summaries.exists(),
            "questions": sorted(set(note.question_sets.values_list("format", flat=True))),
            "podcast": False,  # wk5
            "study_plans": [],  # wk6
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
        question_format = request.data.get("question_format", "")
        if OutputType.QUESTIONS.value in outputs:
            if question_format not in QUESTION_FORMATS:
                raise APIError(
                    "'question_format' is required with questions.",
                    code=ErrorCode.VALIDATION_ERROR,
                    status_code=400,
                    details={"allowed": list(QUESTION_FORMATS)},
                )
        else:
            question_format = ""
        in_flight = note.jobs.filter(
            status__in=[GenerationJob.PENDING, GenerationJob.PROCESSING]
        ).exists()
        if in_flight:
            raise APIError(
                "A generation job for this note is already running.",
                code=ErrorCode.JOB_ALREADY_RUNNING,
                status_code=409,
            )
        job = GenerationJob.objects.create(
            note=note,
            owner=request.user,
            requested_outputs=outputs,
            question_format=question_format,
        )
        run_generation.delay(job.pk)
        return Response({"job_id": job.pk}, status=status.HTTP_202_ACCEPTED)


class NoteQuestionsView(NotesAPIView):
    permission_classes = [HasAIEntitlement]

    def get(self, request, pk):
        note = get_owned_note(request, pk)
        sets = note.question_sets.all()
        requested_format = request.query_params.get("format")
        if requested_format:
            sets = sets.filter(format=requested_format)
        return Response(
            {"note_id": note.pk, "sets": QuestionSetSerializer(sets, many=True).data}
        )


class JobDetailView(NotesAPIView):
    permission_classes = [HasAIEntitlement]

    def get(self, request, job_id):
        job = GenerationJob.objects.filter(pk=job_id, owner=request.user).first()
        if job is None:
            raise APIError("Job not found.", code=ErrorCode.NOT_FOUND, status_code=404)
        return Response(GenerationJobSerializer(job).data)


class NoteSummaryView(NotesAPIView):
    permission_classes = [HasAIEntitlement]

    def get(self, request, pk):
        note = get_owned_note(request, pk)
        summary = note.summaries.first()  # newest first per Meta ordering
        if summary is None:
            raise APIError(
                "No summary exists for this note yet.", code=ErrorCode.NOT_FOUND, status_code=404
            )
        return Response(SummarySerializer(summary).data)
