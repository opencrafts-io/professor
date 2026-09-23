"""Contract-level happy path and failure path, HTTP only: upload -> generate -> poll -> fetch."""

from django.core.files.uploadedfile import SimpleUploadedFile

from notes.llm.base import OutputType
from notes.llm.fake import FakeClient


def _upload(auth_client):
    pdf = SimpleUploadedFile("lecture3.pdf", b"%PDF-1.4 fake body", content_type="application/pdf")
    response = auth_client.post("/api/notes/", {"file": pdf}, format="multipart")
    assert response.status_code == 201
    return response.data["id"]


def test_upload_generate_poll_fetch_summary_and_questions(auth_client):
    note_id = _upload(auth_client)

    response = auth_client.post(
        f"/api/notes/{note_id}/generate/",
        {"outputs": ["summary", "questions", "podcast"], "question_format": "flashcard"},
        format="json",
    )
    assert response.status_code == 202
    job_id = response.data["job_id"]

    job = auth_client.get(f"/api/notes/jobs/{job_id}/").data
    assert job["status"] == "done"
    assert job["failure_code"] is None

    summary = auth_client.get(f"/api/notes/{note_id}/summary/").data
    assert summary["note_id"] == note_id
    assert summary["content"]["title"]
    assert summary["content"]["sections"]

    questions = auth_client.get(f"/api/notes/{note_id}/questions/?format=flashcard").data
    assert len(questions["sets"]) == 1
    assert questions["sets"][0]["questions"]

    podcast = auth_client.get(f"/api/notes/{note_id}/podcast/").data
    assert podcast["script"]
    assert podcast["audio_url"]

    detail = auth_client.get(f"/api/notes/{note_id}/").data
    assert detail["artifacts"]["summary"] is True
    assert detail["artifacts"]["questions"] == ["flashcard"]
    assert detail["artifacts"]["podcast"] is True


def test_pipeline_surfaces_llm_failure_via_job_poll(auth_client, monkeypatch):
    bad = {"title": 5}
    monkeypatch.setattr(
        "notes.services.generation.get_llm_client",
        lambda: FakeClient(script=[{OutputType.SUMMARY: bad}, {OutputType.SUMMARY: bad}]),
    )
    note_id = _upload(auth_client)

    response = auth_client.post(
        f"/api/notes/{note_id}/generate/", {"outputs": ["summary"]}, format="json"
    )
    job = auth_client.get(f"/api/notes/jobs/{response.data['job_id']}/").data
    assert job["status"] == "failed"
    assert job["failure_code"] == "llm_invalid_output"

    assert auth_client.get(f"/api/notes/{note_id}/summary/").status_code == 404
