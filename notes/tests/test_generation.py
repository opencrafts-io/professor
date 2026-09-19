import pytest
from django.core.files.base import ContentFile

from courses.models import StudentCourse
from institutions.models import Institution
from notes.llm.base import PROMPT_VERSION, OutputType
from notes.llm.fake import FakeClient
from notes.models import GenerationJob, Note
from notes.services.generation import run_generation_job
from users.models import StudentProfile

GOOD = {"title": "t", "sections": [{"heading": "h", "points": ["p"]}]}
BAD = {"title": 5}


@pytest.fixture
def note(user):
    note = Note(owner=user, original_filename="a.pdf", size_bytes=9)
    note.file.save("a.pdf", ContentFile(b"%PDF-fake"), save=True)
    return note


@pytest.fixture
def job(note, user):
    return GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])


def test_happy_path_persists_summary_and_marks_done(job):
    client = FakeClient(responses={OutputType.SUMMARY: GOOD}, input_tokens=100, output_tokens=20)
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert (job.input_tokens, job.output_tokens) == (100, 20)
    assert job.prompt_version == PROMPT_VERSION
    summary = job.note.summaries.get()
    assert summary.content == GOOD
    assert summary.prompt_version == PROMPT_VERSION
    assert summary.job == job


def test_invalid_output_retries_once_with_corrective_note(job):
    client = FakeClient(
        script=[{OutputType.SUMMARY: BAD}, {OutputType.SUMMARY: GOOD}],
        input_tokens=100,
        output_tokens=20,
    )
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert len(client.calls) == 2
    _, second_context = client.calls[1]
    assert second_context.corrective_note != ""
    # both calls were paid for
    assert (job.input_tokens, job.output_tokens) == (200, 40)
    assert job.note.summaries.get().content == GOOD


def test_invalid_output_twice_fails_job(job):
    client = FakeClient(script=[{OutputType.SUMMARY: BAD}, {OutputType.SUMMARY: BAD}])
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_INVALID_OUTPUT
    assert not job.note.summaries.exists()
    assert len(client.calls) == 2


def test_provider_error_fails_job(job):
    class ExplodingClient:
        def generate(self, pdf_bytes, output_types, context):
            raise RuntimeError("boom")

    run_generation_job(job.pk, client=ExplodingClient())
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_PROVIDER
    assert not job.note.summaries.exists()


def test_unreadable_file_fails_without_calling_llm(user):
    note = Note.objects.create(
        owner=user, original_filename="a.pdf", size_bytes=1, file="notes/x/missing.pdf"
    )
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_FILE_UNREADABLE
    assert client.calls == []


def test_finished_job_is_not_rerun(job):
    job.mark_done(input_tokens=1, output_tokens=1)
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    assert client.calls == []
    job.refresh_from_db()
    assert (job.input_tokens, job.output_tokens) == (1, 1)


def test_context_uses_course_fields_when_linked(note, user):
    institution = Institution.objects.create(
        name="Academia University",
        web_pages=["https://academia.example"],
        domains=["academia.example"],
        country="Kenya",
    )
    student = StudentProfile.objects.create(user=user, student_id="student-001")
    note.course = StudentCourse.objects.create(
        student=student,
        institution=institution,
        code="MAT 2201",
        title="Engineering Mathematics II",
    )
    note.save()
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    _, context = client.calls[0]
    assert context.course_name == "Engineering Mathematics II"
    assert context.course_code == "MAT 2201"


def test_context_falls_back_to_course_label(note, user):
    note.course_label = "Thermodynamics I"
    note.save()
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    _, context = client.calls[0]
    assert context.course_name == "Thermodynamics I"
    assert context.course_code == ""


@pytest.fixture
def docx_note(user):
    note = Note(owner=user, original_filename="lecture.docx", size_bytes=9)
    note.file.save("lecture.docx", ContentFile(b"PK\x03\x04 fake office"), save=True)
    return note


@pytest.fixture
def docx_job(docx_note, user):
    return GenerationJob.objects.create(
        note=docx_note, owner=user, requested_outputs=["summary"]
    )


def test_document_is_converted_to_markdown_and_sent_to_llm(docx_job):
    class MarkdownConverter:
        def __init__(self):
            self.calls = []

        def to_markdown(self, file_bytes, filename):
            self.calls.append((file_bytes, filename))
            return "# Lecture\n\nNewton's laws"

    client = FakeClient()
    converter = MarkdownConverter()
    run_generation_job(docx_job.pk, client=client, markdown_converter=converter)

    docx_job.refresh_from_db()
    assert docx_job.status == GenerationJob.DONE
    assert converter.calls == [(b"PK\x03\x04 fake office", "lecture.docx")]
    assert client.document_text_seen == ["# Lecture\n\nNewton's laws"]


def test_document_ingestion_has_no_pdf_fallback():
    from io import BytesIO

    from notes.services.generation import _document_for

    class SourceFile:
        name = "lecture.docx"

        def open(self, mode):
            return BytesIO(b"PK\x03\x04 fake office")

    class Note:
        file = SourceFile()
        original_filename = "lecture.docx"

    class MarkdownConverter:
        def to_markdown(self, file_bytes, filename):
            return "# Lecture"

    assert _document_for(Note(), MarkdownConverter()) == "# Lecture"


def test_conversion_failure_fails_job_without_llm_call(docx_job):
    from notes.convert.base import ConversionError

    class MarkdownConverter:
        def to_markdown(self, file_bytes, filename):
            raise ConversionError("conversion failed")

    client = FakeClient()
    run_generation_job(docx_job.pk, client=client, markdown_converter=MarkdownConverter())
    docx_job.refresh_from_db()
    assert docx_job.status == GenerationJob.FAILED
    assert docx_job.failure_code == GenerationJob.FAILURE_CONVERSION
    assert client.calls == []


def test_worker_task_runs_job(job, settings):
    settings.AI_LLM_BACKEND = "fake"
    from notes.tasks import run_generation

    run_generation.delay(job.pk)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert job.note.summaries.exists()
