import pytest

from notes.models import GenerationJob, Note


@pytest.fixture
def job(user):
    note = Note.objects.create(
        owner=user, original_filename="a.pdf", size_bytes=1, file="notes/x/a.pdf"
    )
    return GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])


def test_job_starts_pending(job):
    assert job.status == GenerationJob.PENDING
    assert job.started_at is None and job.finished_at is None


def test_mark_processing_then_done(job):
    job.mark_processing()
    assert job.status == GenerationJob.PROCESSING and job.started_at is not None
    job.mark_done(input_tokens=100, output_tokens=20)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert (job.input_tokens, job.output_tokens) == (100, 20)
    assert job.finished_at is not None


def test_mark_failed_records_code(job):
    job.mark_failed("llm_invalid_output", "schema mismatch")
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == "llm_invalid_output"
    assert job.finished_at is not None
