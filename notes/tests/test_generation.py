import pytest
from django.core.files.base import ContentFile

from courses.models import Course, SemesterInfo
from notes.llm.base import PROMPT_VERSION, OutputType
from notes.llm.fake import FakeClient
from notes.models import GenerationJob, Note
from notes.services.generation import run_generation_job

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
    semester = SemesterInfo.objects.create(
        code="S1", name="Sem 1", start_date="2026-09-01", end_date="2026-12-15"
    )
    note.course = Course.objects.create(
        course_code="MAT 2201", course_name="Engineering Mathematics II", semester=semester
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


def test_docx_note_is_converted_and_pdf_sent_to_llm(docx_job):
    from notes.convert.fake import FAKE_PDF, FakeConverter

    client, converter = FakeClient(), FakeConverter()
    run_generation_job(docx_job.pk, client=client, converter=converter)
    docx_job.refresh_from_db()
    assert docx_job.status == GenerationJob.DONE
    assert converter.calls == ["lecture.docx"]
    assert client.pdf_bytes_seen == [FAKE_PDF]
    note = docx_job.note
    note.refresh_from_db()
    assert note.converted_file.name.endswith(".pdf")


def test_converted_pdf_is_cached_across_jobs(docx_note, docx_job, user):
    from notes.convert.fake import FakeConverter

    run_generation_job(docx_job.pk, client=FakeClient(), converter=FakeConverter())
    second_job = GenerationJob.objects.create(
        note=docx_note, owner=user, requested_outputs=["summary"]
    )
    converter = FakeConverter()
    run_generation_job(second_job.pk, client=FakeClient(), converter=converter)
    second_job.refresh_from_db()
    assert second_job.status == GenerationJob.DONE
    assert converter.calls == []


def test_conversion_failure_fails_job_without_llm_call(docx_job):
    from notes.convert.base import ConversionError
    from notes.convert.fake import FakeConverter

    client = FakeClient()
    converter = FakeConverter(error=ConversionError("upstream down"))
    run_generation_job(docx_job.pk, client=client, converter=converter)
    docx_job.refresh_from_db()
    assert docx_job.status == GenerationJob.FAILED
    assert docx_job.failure_code == GenerationJob.FAILURE_CONVERSION
    assert client.calls == []


def test_pdf_note_never_touches_converter(job):
    from notes.convert.fake import FakeConverter

    converter = FakeConverter()
    run_generation_job(job.pk, client=FakeClient(), converter=converter)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert converter.calls == []


def test_worker_task_runs_job_via_settings_backend(job, settings):
    settings.AI_LLM_BACKEND = "fake"
    from notes.tasks import run_generation

    run_generation.delay(job.pk)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert job.note.summaries.exists()
