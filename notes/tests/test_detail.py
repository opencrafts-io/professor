import uuid

import pytest

from notes.models import Note
from users.models import User


@pytest.fixture
def note(user):
    return Note.objects.create(owner=user, original_filename="a.pdf", size_bytes=1, file="n/a.pdf")


def test_detail_returns_note_with_artifacts_stub(auth_client, note):
    response = auth_client.get(f"/api/notes/{note.pk}/")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == note.pk
    assert body["artifacts"] == {
        "summary": False,
        "questions": [],
        "podcast": False,
        "study_plans": [],
    }


def test_detail_of_other_users_note_is_404(auth_client, db):
    other = User.objects.create(user_id=uuid.uuid4(), name="Other")
    other_note = Note.objects.create(
        owner=other, original_filename="b.pdf", size_bytes=1, file="n/b.pdf"
    )
    response = auth_client.get(f"/api/notes/{other_note.pk}/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_removes_note(auth_client, note):
    response = auth_client.delete(f"/api/notes/{note.pk}/")
    assert response.status_code == 204
    assert not Note.objects.filter(pk=note.pk).exists()
