"""Per-user daily and monthly quotas: counted from existing rows, limits from
settings, 429 quota_exceeded with details when a limit is hit."""

from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from notes.models import GenerationJob, Note

PDF_BYTES = b"%PDF-1.4 fake minimal body"


def _pdf(name="q.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def _note(user, name="a.pdf"):
    note = Note(owner=user, original_filename=name, size_bytes=9)
    note.file.save(name, ContentFile(b"%PDF-fake"), save=True)
    return note


def _month_start():
    return timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def test_upload_blocked_at_daily_limit(auth_client, user, settings):
    settings.AI_QUOTAS = {"uploads_per_day": 1}
    assert auth_client.post("/api/notes/", {"file": _pdf()}, format="multipart").status_code == 201
    response = auth_client.post("/api/notes/", {"file": _pdf("b.pdf")}, format="multipart")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "quota_exceeded"
    assert response.json()["error"]["details"] == {
        "quota": "uploads_per_day",
        "limit": 1,
        "used": 1,
    }
    # the blocked upload must not have been stored
    assert Note.objects.filter(owner=user).count() == 1


def test_generation_blocked_at_daily_limit(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_day": 1}
    note = _note(user)
    first = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert first.status_code == 202
    response = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "quota_exceeded"
    assert GenerationJob.objects.filter(owner=user).count() == 1


def test_plan_jobs_count_toward_generation_quota(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_day": 1}
    note = _note(user)
    plan_response = auth_client.post(
        "/api/notes/study-plans/", {"note_ids": [note.pk]}, format="json"
    )
    assert plan_response.status_code == 202
    response = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert response.status_code == 429


def test_plan_creation_itself_respects_generation_quota(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_day": 1}
    note = _note(user)
    auth_client.post(f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json")
    response = auth_client.post(
        "/api/notes/study-plans/", {"note_ids": [note.pk]}, format="json"
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "quota_exceeded"
    # no orphan plan row behind the rejected request
    from notes.models import StudyPlan

    assert not StudyPlan.objects.filter(owner=user).exists()


def test_podcasts_have_their_own_tighter_limit(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_day": 10, "podcasts_per_day": 1}
    note = _note(user)
    first = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["podcast"]}, format="json"
    )
    assert first.status_code == 202
    other = _note(user, "b.pdf")
    response = auth_client.post(
        f"/api/notes/{other.pk}/generate/", {"outputs": ["podcast"]}, format="json"
    )
    assert response.status_code == 429
    assert response.json()["error"]["details"]["quota"] == "podcasts_per_day"
    # cheaper outputs are still within the general quota
    ok = auth_client.post(
        f"/api/notes/{other.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert ok.status_code == 202


def test_only_todays_usage_counts(auth_client, user, settings):
    settings.AI_QUOTAS = {"uploads_per_day": 1}
    auth_client.post("/api/notes/", {"file": _pdf()}, format="multipart")
    # push the upload just before midnight UTC: quota days are calendar days
    yesterday_night = timezone.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(minutes=1)
    Note.objects.filter(owner=user).update(uploaded_at=yesterday_night)
    response = auth_client.post("/api/notes/", {"file": _pdf("b.pdf")}, format="multipart")
    assert response.status_code == 201


def test_other_users_usage_does_not_count(auth_client, user, settings):
    import uuid

    from users.models import User

    settings.AI_QUOTAS = {"uploads_per_day": 1}
    other = User.objects.create(user_id=uuid.uuid4(), name="Other")
    Note.objects.create(owner=other, original_filename="o.pdf", size_bytes=1, file="n/o.pdf")
    response = auth_client.post("/api/notes/", {"file": _pdf()}, format="multipart")
    assert response.status_code == 201


def test_missing_quota_key_means_unlimited(auth_client, settings):
    settings.AI_QUOTAS = {}
    for i in range(3):
        response = auth_client.post(
            "/api/notes/", {"file": _pdf(f"f{i}.pdf")}, format="multipart"
        )
        assert response.status_code == 201


def test_generation_blocked_at_monthly_limit(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_month": 1}
    note = _note(user)
    first = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert first.status_code == 202
    response = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert response.status_code == 429
    assert response.json()["error"]["details"] == {
        "quota": "generations_per_month",
        "limit": 1,
        "used": 1,
    }
    assert "month" in response.json()["error"]["message"].lower()


def test_usage_earlier_in_the_month_counts(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_month": 1}
    note = _note(user)
    auth_client.post(f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json")
    GenerationJob.objects.filter(owner=user).update(created_at=_month_start())
    response = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert response.status_code == 429


def test_last_months_usage_does_not_count(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_month": 1}
    note = _note(user)
    auth_client.post(f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json")
    GenerationJob.objects.filter(owner=user).update(
        created_at=_month_start() - timedelta(minutes=1)
    )
    response = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert response.status_code == 202


def test_podcasts_have_their_own_monthly_cap(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_month": 10, "podcasts_per_month": 1}
    note = _note(user)
    first = auth_client.post(
        f"/api/notes/{note.pk}/generate/", {"outputs": ["podcast"]}, format="json"
    )
    assert first.status_code == 202
    other = _note(user, "b.pdf")
    response = auth_client.post(
        f"/api/notes/{other.pk}/generate/", {"outputs": ["podcast"]}, format="json"
    )
    assert response.status_code == 429
    assert response.json()["error"]["details"]["quota"] == "podcasts_per_month"
    # cheaper outputs are still within the general quota
    ok = auth_client.post(
        f"/api/notes/{other.pk}/generate/", {"outputs": ["summary"]}, format="json"
    )
    assert ok.status_code == 202


def test_plan_creation_respects_monthly_quota(auth_client, user, settings):
    settings.AI_QUOTAS = {"generations_per_month": 1}
    note = _note(user)
    auth_client.post(f"/api/notes/{note.pk}/generate/", {"outputs": ["summary"]}, format="json")
    response = auth_client.post(
        "/api/notes/study-plans/", {"note_ids": [note.pk]}, format="json"
    )
    assert response.status_code == 429
    from notes.models import StudyPlan

    assert not StudyPlan.objects.filter(owner=user).exists()


def test_default_quotas_are_configured(settings):
    for key in (
        "uploads_per_day",
        "generations_per_day",
        "podcasts_per_day",
        "generations_per_month",
        "podcasts_per_month",
    ):
        assert isinstance(settings.AI_QUOTAS[key], int)
