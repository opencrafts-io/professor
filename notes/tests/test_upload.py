import uuid

from django.core.files.uploadedfile import SimpleUploadedFile

from notes.models import Note
from users.models import User

PDF_BYTES = b"%PDF-1.4 fake minimal body"


def _pdf(name="lecture.pdf", content=PDF_BYTES):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_upload_happy_path(auth_client, user):
    response = auth_client.post("/api/notes/", {"file": _pdf()}, format="multipart")
    assert response.status_code == 201, response.content
    note = Note.objects.get(owner=user)
    assert note.original_filename == "lecture.pdf"
    assert response.json()["id"] == note.pk
    assert note.file.name.startswith(f"notes/{user.user_id}/")


def test_upload_rejects_non_pdf(auth_client):
    fake = SimpleUploadedFile("notes.pdf", b"MZ not a pdf", content_type="application/pdf")
    response = auth_client.post("/api/notes/", {"file": fake}, format="multipart")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "note_not_pdf"


def test_upload_rejects_oversize(auth_client, settings):
    settings.NOTES_MAX_UPLOAD_BYTES = 10
    response = auth_client.post("/api/notes/", {"file": _pdf()}, format="multipart")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_requires_auth(api_client):
    response = api_client.post("/api/notes/", {"file": _pdf()}, format="multipart")
    assert response.status_code in (401, 403)


def test_upload_denied_without_entitlement(auth_client, settings):
    settings.AI_ENTITLEMENT_MODE = "verisafe"
    response = auth_client.post("/api/notes/", {"file": _pdf()}, format="multipart")
    assert response.status_code == 403


def test_upload_rejects_unknown_course(auth_client):
    response = auth_client.post(
        "/api/notes/", {"file": _pdf(), "course_id": 999999}, format="multipart"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_list_returns_only_own_notes(auth_client, user, db):
    other = User.objects.create(user_id=uuid.uuid4(), name="Other")
    Note.objects.create(owner=user, original_filename="mine.pdf", size_bytes=1, file="n/a.pdf")
    Note.objects.create(owner=other, original_filename="theirs.pdf", size_bytes=1, file="n/b.pdf")
    response = auth_client.get("/api/notes/")
    names = [n["original_filename"] for n in response.json()["results"]]
    assert names == ["mine.pdf"]
