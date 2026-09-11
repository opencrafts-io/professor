import pytest
from django.core.files.base import ContentFile

from notes.models import GenerationJob, Note


@pytest.fixture
def note(user):
    note = Note(owner=user, original_filename="a.pdf", size_bytes=9)
    note.file.save("a.pdf", ContentFile(b"%PDF-fake"), save=True)
    return note


def generate_url(note):
    return f"/api/notes/{note.pk}/generate/"


def test_generate_dispatches_job_and_returns_202(auth_client, note):
    response = auth_client.post(generate_url(note), {"outputs": ["summary"]}, format="json")
    assert response.status_code == 202
    job = GenerationJob.objects.get(pk=response.data["job_id"])
    assert job.note == note
    assert job.requested_outputs == ["summary"]
    # celery eager + fake backend: the job has already run to completion
    assert job.status == GenerationJob.DONE
    assert note.summaries.exists()


def test_generate_requires_outputs_list(auth_client, note):
    response = auth_client.post(generate_url(note), {}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_generate_rejects_unknown_output(auth_client, note):
    response = auth_client.post(generate_url(note), {"outputs": ["essay"]}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_generate_rejects_not_yet_supported_output(auth_client, note):
    response = auth_client.post(generate_url(note), {"outputs": ["questions"]}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_generate_conflicts_while_job_in_flight(auth_client, note, user):
    GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    response = auth_client.post(generate_url(note), {"outputs": ["summary"]}, format="json")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "job_already_running"


def test_generate_404_for_other_users_note(api_client, note):
    import uuid

    from users.models import User

    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    api_client.force_authenticate(user=stranger)
    response = api_client.post(generate_url(note), {"outputs": ["summary"]}, format="json")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_generate_403_without_entitlement(auth_client, note, settings):
    settings.AI_ENTITLEMENT_MODE = "verisafe"
    response = auth_client.post(generate_url(note), {"outputs": ["summary"]}, format="json")
    assert response.status_code == 403
