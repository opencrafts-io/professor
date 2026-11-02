"""Transient provider errors re-queue the task with backoff instead of
failing the job on the first 503; everything else still fails immediately."""

import pytest
from django.core.files.base import ContentFile

from notes.llm.base import LLMProviderError, OutputType
from notes.llm.fake import FakeClient
from notes.models import GenerationJob, Note
from notes.tasks import run_generation

GOOD = {"title": "t", "sections": [{"heading": "h", "points": ["p"]}]}


@pytest.fixture
def job(user):
    note = Note(owner=user, original_filename="a.pdf", size_bytes=9)
    note.file.save("a.pdf", ContentFile(b"%PDF-fake"), save=True)
    return GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])


class FlakyClient:
    """Raises a provider error for the first `failures` calls, then succeeds."""

    def __init__(self, failures):
        self.failures = failures
        self.calls = 0
        self._inner = FakeClient(responses={OutputType.SUMMARY: GOOD})

    def generate(self, document, output_types, context):
        self.calls += 1
        if self.calls <= self.failures:
            raise LLMProviderError("503 model overloaded")
        return self._inner.generate(document, output_types, context)


def test_transient_provider_error_is_retried_until_success(job, monkeypatch):
    client = FlakyClient(failures=2)
    monkeypatch.setattr("notes.services.generation.get_llm_client", lambda: client)
    run_generation.delay(job.pk)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert client.calls == 3
    assert job.note.summaries.exists()


def test_persistent_provider_error_fails_after_retries(job, monkeypatch):
    client = FlakyClient(failures=100)
    monkeypatch.setattr("notes.services.generation.get_llm_client", lambda: client)
    run_generation.delay(job.pk)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_PROVIDER
    assert "503" in job.failure_message
    assert client.calls == 4  # the first attempt plus max_retries


def test_non_provider_errors_are_not_retried(job, monkeypatch):
    calls = {"n": 0}

    class ExplodingClient:
        def generate(self, document, output_types, context):
            calls["n"] += 1
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "notes.services.generation.get_llm_client", lambda: ExplodingClient()
    )
    run_generation.delay(job.pk)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_PROVIDER
    assert calls["n"] == 1
