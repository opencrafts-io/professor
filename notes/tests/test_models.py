import pytest

from notes.models import GenerationJob, Note, Summary, note_upload_path


@pytest.fixture
def note(user):
    return Note.objects.create(
        owner=user, original_filename="lecture3.pdf", size_bytes=1234, file="notes/x/y.pdf"
    )


def test_note_defaults(note, user):
    assert note.owner == user
    assert note.course is None
    assert note.course_label == ""
    assert note.uploaded_at is not None


def test_upload_path_is_owner_scoped_and_unique(note):
    p1 = note_upload_path(note, "whatever.pdf")
    p2 = note_upload_path(note, "whatever.pdf")
    assert p1.startswith(f"notes/{note.owner.user_id}/")
    assert p1.endswith(".pdf")
    assert p1 != p2


def test_summary_belongs_to_note_and_job(note, user):
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    summary = Summary.objects.create(
        note=note, job=job, content={"title": "t", "sections": []}, prompt_version="v1"
    )
    assert summary in note.summaries.all()
    assert summary.job == job
    assert summary.created_at is not None


def test_latest_summary_wins(note, user):
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    Summary.objects.create(note=note, job=job, content={"title": "old"}, prompt_version="v1")
    newer = Summary.objects.create(note=note, job=job, content={"title": "new"}, prompt_version="v1")
    assert note.summaries.first() == newer


def test_summary_survives_job_deletion(note, user):
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    summary = Summary.objects.create(note=note, job=job, content={"title": "t"}, prompt_version="v1")
    job.delete()
    summary.refresh_from_db()
    assert summary.job is None
