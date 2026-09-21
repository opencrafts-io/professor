import uuid

import pytest
from django.core.files.base import ContentFile

from notes.models import GenerationJob, Note, Summary
from users.models import User

CONTENT = {"title": "t", "sections": [{"heading": "h", "points": ["p"]}]}


@pytest.fixture
def note(user):
    note = Note(owner=user, original_filename="a.pdf", size_bytes=9)
    note.file.save("a.pdf", ContentFile(b"%PDF-fake"), save=True)
    return note


@pytest.fixture
def job(note, user):
    return GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])


def test_job_endpoint_matches_contract_shape(auth_client, job):
    response = auth_client.get(f"/api/notes/jobs/{job.pk}/")
    assert response.status_code == 200
    data = response.data
    assert data["id"] == job.pk
    assert data["note_id"] == job.note_id
    assert data["outputs"] == ["summary"]
    assert data["status"] == "pending"
    assert data["failure_code"] is None
    assert data["failure_message"] is None
    assert data["created_at"] is not None
    assert data["finished_at"] is None


def test_job_endpoint_surfaces_failure_code(auth_client, job):
    job.mark_failed(GenerationJob.FAILURE_INVALID_OUTPUT, "schema mismatch")
    response = auth_client.get(f"/api/notes/jobs/{job.pk}/")
    assert response.data["status"] == "failed"
    assert response.data["failure_code"] == "llm_invalid_output"
    assert response.data["failure_message"] == "schema mismatch"
    assert response.data["finished_at"] is not None


def test_job_endpoint_404_for_other_users_job(api_client, job):
    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    api_client.force_authenticate(user=stranger)
    response = api_client.get(f"/api/notes/jobs/{job.pk}/")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_summary_404_before_one_exists(auth_client, note):
    response = auth_client.get(f"/api/notes/{note.pk}/summary/")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_summary_returns_latest_content(auth_client, note, job):
    Summary.objects.create(note=note, job=job, content={"title": "old"}, prompt_version="v1")
    Summary.objects.create(note=note, job=job, content=CONTENT, prompt_version="v1")
    response = auth_client.get(f"/api/notes/{note.pk}/summary/")
    assert response.status_code == 200
    assert response.data["note_id"] == note.pk
    assert response.data["content"] == CONTENT
    assert response.data["generated_at"] is not None


def test_summary_owner_scoped(api_client, note, job):
    Summary.objects.create(note=note, job=job, content=CONTENT, prompt_version="v1")
    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    api_client.force_authenticate(user=stranger)
    response = api_client.get(f"/api/notes/{note.pk}/summary/")
    assert response.status_code == 404


FLASHCARDS = [{"front": "Q", "back": "A"}]
MCQS = [{"question": "q", "choices": ["a", "b"], "answer_index": 0, "explanation": "e"}]


def _make_set(note, job, fmt, questions):
    from notes.models import QuestionSet

    return QuestionSet.objects.create(
        note=note, job=job, format=fmt, questions=questions, prompt_version="v3"
    )


def test_questions_endpoint_lists_sets_per_contract(auth_client, note, job):
    _make_set(note, job, "flashcard", FLASHCARDS)
    _make_set(note, job, "mcq", MCQS)
    response = auth_client.get(f"/api/notes/{note.pk}/questions/")
    assert response.status_code == 200
    assert response.data["note_id"] == note.pk
    sets = response.data["sets"]
    assert {s["format"] for s in sets} == {"flashcard", "mcq"}
    for s in sets:
        assert set(s) == {"id", "format", "generated_at", "questions"}
    flashcard_set = next(s for s in sets if s["format"] == "flashcard")
    assert flashcard_set["questions"] == FLASHCARDS


def test_questions_endpoint_filters_by_format(auth_client, note, job):
    _make_set(note, job, "flashcard", FLASHCARDS)
    _make_set(note, job, "mcq", MCQS)
    response = auth_client.get(f"/api/notes/{note.pk}/questions/?format=mcq")
    assert [s["format"] for s in response.data["sets"]] == ["mcq"]


def test_questions_endpoint_empty_when_none(auth_client, note):
    response = auth_client.get(f"/api/notes/{note.pk}/questions/")
    assert response.status_code == 200
    assert response.data["sets"] == []


def test_questions_endpoint_owner_scoped(api_client, note, job):
    _make_set(note, job, "flashcard", FLASHCARDS)
    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    api_client.force_authenticate(user=stranger)
    assert api_client.get(f"/api/notes/{note.pk}/questions/").status_code == 404


def test_note_detail_lists_question_formats(auth_client, note, job):
    _make_set(note, job, "flashcard", FLASHCARDS)
    _make_set(note, job, "flashcard", FLASHCARDS)
    _make_set(note, job, "mcq", MCQS)
    artifacts = auth_client.get(f"/api/notes/{note.pk}/").data["artifacts"]
    assert artifacts["questions"] == ["flashcard", "mcq"]


def test_note_detail_reports_summary_artifact(auth_client, note, job):
    assert auth_client.get(f"/api/notes/{note.pk}/").data["artifacts"]["summary"] is False
    Summary.objects.create(note=note, job=job, content=CONTENT, prompt_version="v1")
    assert auth_client.get(f"/api/notes/{note.pk}/").data["artifacts"]["summary"] is True
