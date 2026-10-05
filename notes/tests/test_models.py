import pytest

from notes.models import (
    GenerationJob,
    Note,
    QuestionSet,
    StudyPlan,
    Summary,
    note_upload_path,
)


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


def test_study_plan_links_owner_notes_and_jobs(note, user):
    other_note = Note.objects.create(
        owner=user, original_filename="b.pdf", size_bytes=1, file="notes/x/b.pdf"
    )
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set([note, other_note])
    assert plan.course is None
    assert plan.topics == []
    assert plan.status == GenerationJob.PENDING
    assert set(plan.notes.all()) == {note, other_note}
    assert plan in note.study_plans.all()

    job = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    assert job.note is None
    job.mark_done(input_tokens=1, output_tokens=1)
    assert plan.status == GenerationJob.DONE


def test_study_plan_status_follows_latest_job(note, user):
    plan = StudyPlan.objects.create(owner=user)
    first = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    first.mark_failed("llm_provider_error", "boom")
    GenerationJob.objects.create(owner=user, study_plan=plan, requested_outputs=["study_plan"])
    assert plan.status == GenerationJob.PENDING


def test_question_set_belongs_to_note_with_format(note, user):
    job = GenerationJob.objects.create(
        note=note, owner=user, requested_outputs=["questions"], question_format="flashcard"
    )
    question_set = QuestionSet.objects.create(
        note=note,
        job=job,
        format="flashcard",
        questions=[{"front": "Q", "back": "A"}],
        prompt_version="v3",
    )
    assert question_set in note.question_sets.all()
    assert job.question_format == "flashcard"
    assert question_set.created_at is not None


def test_question_set_survives_job_deletion(note, user):
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["questions"])
    question_set = QuestionSet.objects.create(
        note=note, job=job, format="mcq", questions=[], prompt_version="v3"
    )
    job.delete()
    question_set.refresh_from_db()
    assert question_set.job is None


def test_summary_survives_job_deletion(note, user):
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    summary = Summary.objects.create(note=note, job=job, content={"title": "t"}, prompt_version="v1")
    job.delete()
    summary.refresh_from_db()
    assert summary.job is None
