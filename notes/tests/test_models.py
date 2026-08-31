import pytest

from notes.models import Note, note_upload_path


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
