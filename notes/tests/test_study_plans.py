import uuid

import pytest
from django.core.files.base import ContentFile

from notes.models import GenerationJob, Note, StudyPlan
from users.models import User


@pytest.fixture
def notes(user):
    made = []
    for i in range(2):
        note = Note(owner=user, original_filename=f"n{i}.docx", size_bytes=9)
        note.file.save(f"n{i}.docx", ContentFile(b"PK\x03\x04 x"), save=True)
        # pre-cached markdown so eager jobs skip real conversion
        note.converted_markdown = f"# Notes {i}\n\ncontent {i}"
        note.save(update_fields=["converted_markdown"])
        made.append(note)
    return made


def test_create_study_plan_runs_to_topics(auth_client, notes):
    response = auth_client.post(
        "/api/notes/study-plans/",
        {"note_ids": [n.pk for n in notes]},
        format="json",
    )
    assert response.status_code == 202, response.content
    plan = StudyPlan.objects.get(pk=response.data["study_plan_id"])
    job = GenerationJob.objects.get(pk=response.data["job_id"])
    assert job.study_plan == plan
    assert set(plan.notes.all()) == set(notes)
    plan.refresh_from_db()
    assert plan.status == GenerationJob.DONE  # celery eager + fake backend
    assert plan.topics


def test_create_requires_note_ids(auth_client):
    response = auth_client.post("/api/notes/study-plans/", {}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_create_rejects_foreign_or_unknown_notes(auth_client, notes):
    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    foreign = Note.objects.create(
        owner=stranger, original_filename="f.pdf", size_bytes=1, file="n/f.pdf"
    )
    response = auth_client.post(
        "/api/notes/study-plans/",
        {"note_ids": [notes[0].pk, foreign.pk]},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"

    response = auth_client.post(
        "/api/notes/study-plans/", {"note_ids": [999999]}, format="json"
    )
    assert response.status_code == 400


def test_create_rejects_unknown_course(auth_client, notes):
    response = auth_client.post(
        "/api/notes/study-plans/",
        {"note_ids": [notes[0].pk], "course_id": str(uuid.uuid4())},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_plan_detail_matches_contract_shape(auth_client, notes, user):
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set(notes)
    response = auth_client.get(f"/api/notes/study-plans/{plan.pk}/")
    assert response.status_code == 200
    data = response.data
    assert data["id"] == plan.pk
    assert data["course_id"] is None
    assert set(data["note_ids"]) == {n.pk for n in notes}
    assert data["status"] == "pending"
    assert data["topics"] == []
    assert data["generated_at"] is None


def test_plan_detail_owner_scoped(api_client, notes, user):
    plan = StudyPlan.objects.create(owner=user)
    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    api_client.force_authenticate(user=stranger)
    response = api_client.get(f"/api/notes/study-plans/{plan.pk}/")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_regenerate_dispatches_new_job(auth_client, notes, user):
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set(notes)
    response = auth_client.post(f"/api/notes/study-plans/{plan.pk}/regenerate/")
    assert response.status_code == 202
    job = GenerationJob.objects.get(pk=response.data["job_id"])
    assert job.study_plan == plan
    plan.refresh_from_db()
    assert plan.topics  # eager run completed


def test_regenerate_conflicts_while_job_in_flight(auth_client, notes, user):
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set(notes)
    GenerationJob.objects.create(owner=user, study_plan=plan, requested_outputs=["study_plan"])
    response = auth_client.post(f"/api/notes/study-plans/{plan.pk}/regenerate/")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "job_already_running"


def test_note_detail_lists_study_plans(auth_client, notes, user):
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set(notes)
    artifacts = auth_client.get(f"/api/notes/{notes[0].pk}/").data["artifacts"]
    assert artifacts["study_plans"] == [plan.pk]


def test_study_plans_require_entitlement(auth_client, settings):
    settings.AI_ENTITLEMENT_MODE = "verisafe"
    response = auth_client.post("/api/notes/study-plans/", {"note_ids": [1]}, format="json")
    assert response.status_code == 403
