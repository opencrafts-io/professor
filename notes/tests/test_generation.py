import pytest
from django.core.files.base import ContentFile

from courses.models import StudentCourse
from institutions.models import Institution
from notes.llm.base import PROMPT_VERSION, OutputType
from notes.llm.fake import FakeClient
from notes.models import GenerationJob, Note
from notes.services.generation import run_generation_job
from users.models import StudentProfile

GOOD = {"title": "t", "sections": [{"heading": "h", "points": ["p"]}]}
BAD = {"title": 5}


@pytest.fixture
def note(user):
    note = Note(owner=user, original_filename="a.pdf", size_bytes=9)
    note.file.save("a.pdf", ContentFile(b"%PDF-fake"), save=True)
    return note


@pytest.fixture
def job(note, user):
    return GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])


def test_happy_path_persists_summary_and_marks_done(job):
    client = FakeClient(responses={OutputType.SUMMARY: GOOD}, input_tokens=100, output_tokens=20)
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert (job.input_tokens, job.output_tokens) == (100, 20)
    assert job.prompt_version == PROMPT_VERSION
    summary = job.note.summaries.get()
    assert summary.content == GOOD
    assert summary.prompt_version == PROMPT_VERSION
    assert summary.job == job


def test_invalid_output_retries_once_with_corrective_note(job):
    client = FakeClient(
        script=[{OutputType.SUMMARY: BAD}, {OutputType.SUMMARY: GOOD}],
        input_tokens=100,
        output_tokens=20,
    )
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert len(client.calls) == 2
    _, second_context = client.calls[1]
    assert second_context.corrective_note != ""
    # both calls were paid for
    assert (job.input_tokens, job.output_tokens) == (200, 40)
    assert job.note.summaries.get().content == GOOD


def test_invalid_output_twice_fails_job(job):
    client = FakeClient(script=[{OutputType.SUMMARY: BAD}, {OutputType.SUMMARY: BAD}])
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_INVALID_OUTPUT
    assert not job.note.summaries.exists()
    assert len(client.calls) == 2


def test_provider_error_fails_job(job):
    class ExplodingClient:
        def generate(self, pdf_bytes, output_types, context):
            raise RuntimeError("boom")

    run_generation_job(job.pk, client=ExplodingClient())
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_PROVIDER
    assert not job.note.summaries.exists()


def test_unreadable_file_fails_without_calling_llm(user):
    note = Note.objects.create(
        owner=user, original_filename="a.pdf", size_bytes=1, file="notes/x/missing.pdf"
    )
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_FILE_UNREADABLE
    assert client.calls == []


def test_finished_job_is_not_rerun(job):
    job.mark_done(input_tokens=1, output_tokens=1)
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    assert client.calls == []
    job.refresh_from_db()
    assert (job.input_tokens, job.output_tokens) == (1, 1)


def test_context_uses_course_fields_when_linked(note, user):
    institution = Institution.objects.create(
        name="Academia University",
        web_pages=["https://academia.example"],
        domains=["academia.example"],
        country="Kenya",
    )
    student = StudentProfile.objects.create(user=user, student_id="student-001")
    note.course = StudentCourse.objects.create(
        student=student,
        institution=institution,
        code="MAT 2201",
        title="Engineering Mathematics II",
    )
    note.save()
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    _, context = client.calls[0]
    assert context.course_name == "Engineering Mathematics II"
    assert context.course_code == "MAT 2201"


def test_context_falls_back_to_course_label(note, user):
    note.course_label = "Thermodynamics I"
    note.save()
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["summary"])
    client = FakeClient()
    run_generation_job(job.pk, client=client)
    _, context = client.calls[0]
    assert context.course_name == "Thermodynamics I"
    assert context.course_code == ""


@pytest.fixture
def docx_note(user):
    note = Note(owner=user, original_filename="lecture.docx", size_bytes=9)
    note.file.save("lecture.docx", ContentFile(b"PK\x03\x04 fake office"), save=True)
    return note


@pytest.fixture
def docx_job(docx_note, user):
    return GenerationJob.objects.create(
        note=docx_note, owner=user, requested_outputs=["summary"]
    )


def test_document_is_converted_to_markdown_and_sent_to_llm(docx_job):
    class MarkdownConverter:
        def __init__(self):
            self.calls = []

        def to_markdown(self, file_bytes, filename):
            self.calls.append((file_bytes, filename))
            return "# Lecture\n\nNewton's laws"

    client = FakeClient()
    converter = MarkdownConverter()
    run_generation_job(docx_job.pk, client=client, markdown_converter=converter)

    docx_job.refresh_from_db()
    assert docx_job.status == GenerationJob.DONE
    assert converter.calls == [(b"PK\x03\x04 fake office", "lecture.docx")]
    assert client.document_text_seen == ["# Lecture\n\nNewton's laws"]


def test_pdf_falls_back_to_native_bytes_when_extraction_fails(job):
    from notes.convert.base import ConversionError

    class FailingConverter:
        def to_markdown(self, file_bytes, filename):
            raise ConversionError("Document contains no extractable text.")

    client = FakeClient()
    run_generation_job(job.pk, client=client, markdown_converter=FailingConverter())
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert client.document_pdf_seen == [b"%PDF-fake"]
    assert client.document_text_seen == []
    assert job.note.summaries.exists()


def test_converted_markdown_is_cached_across_jobs(docx_note, docx_job, user):
    class CountingConverter:
        def __init__(self):
            self.calls = 0

        def to_markdown(self, file_bytes, filename):
            self.calls += 1
            return "# Lecture"

    converter = CountingConverter()
    run_generation_job(docx_job.pk, client=FakeClient(), markdown_converter=converter)
    docx_note.refresh_from_db()
    assert docx_note.converted_markdown == "# Lecture"

    second_job = GenerationJob.objects.create(
        note=docx_note, owner=user, requested_outputs=["summary"]
    )
    client = FakeClient()
    run_generation_job(second_job.pk, client=client, markdown_converter=converter)
    second_job.refresh_from_db()
    assert second_job.status == GenerationJob.DONE
    assert converter.calls == 1
    assert client.document_text_seen == ["# Lecture"]


def test_pdf_fallback_does_not_cache_markdown(job):
    from notes.convert.base import ConversionError

    class FailingConverter:
        def to_markdown(self, file_bytes, filename):
            raise ConversionError("no extractable text")

    run_generation_job(job.pk, client=FakeClient(), markdown_converter=FailingConverter())
    note = job.note
    note.refresh_from_db()
    assert note.converted_markdown == ""


def test_conversion_failure_fails_job_without_llm_call(docx_job):
    from notes.convert.base import ConversionError

    class MarkdownConverter:
        def to_markdown(self, file_bytes, filename):
            raise ConversionError("conversion failed")

    client = FakeClient()
    run_generation_job(docx_job.pk, client=client, markdown_converter=MarkdownConverter())
    docx_job.refresh_from_db()
    assert docx_job.status == GenerationJob.FAILED
    assert docx_job.failure_code == GenerationJob.FAILURE_CONVERSION
    assert client.calls == []


FLASHCARDS = [{"front": "What is inertia?", "back": "Resistance to change in motion"}]


def test_questions_job_persists_question_set(note, user):
    from notes.models import QuestionSet

    job = GenerationJob.objects.create(
        note=note, owner=user, requested_outputs=["questions"], question_format="flashcard"
    )
    client = FakeClient(responses={OutputType.QUESTIONS: FLASHCARDS})
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    _, context = client.calls[0]
    assert context.question_format == "flashcard"
    question_set = QuestionSet.objects.get(note=note)
    assert question_set.format == "flashcard"
    assert question_set.questions == FLASHCARDS
    assert question_set.job == job


def test_bundled_outputs_use_one_llm_call(note, user):
    from notes.models import QuestionSet

    job = GenerationJob.objects.create(
        note=note,
        owner=user,
        requested_outputs=["summary", "questions"],
        question_format="flashcard",
    )
    client = FakeClient(
        responses={OutputType.SUMMARY: GOOD, OutputType.QUESTIONS: FLASHCARDS}
    )
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert len(client.calls) == 1
    assert note.summaries.count() == 1
    assert QuestionSet.objects.filter(note=note).count() == 1


def test_invalid_questions_fail_after_corrective_retry(note, user):
    job = GenerationJob.objects.create(
        note=note, owner=user, requested_outputs=["questions"], question_format="flashcard"
    )
    bad = [{"front": "no back side"}]
    client = FakeClient(
        script=[{OutputType.QUESTIONS: bad}, {OutputType.QUESTIONS: bad}]
    )
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_INVALID_OUTPUT
    assert len(client.calls) == 2


PODCAST_OUT = {
    "title": "Fourier in five minutes",
    "script": "Alex: Welcome!\nJordan: Fourier series decompose periodic signals.",
}


def test_podcast_job_synthesizes_audio_and_persists(note, user):
    from notes.models import Podcast
    from notes.tts.fake import FakeTTSClient

    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["podcast"])
    client = FakeClient(responses={OutputType.PODCAST: PODCAST_OUT})
    tts = FakeTTSClient()
    run_generation_job(job.pk, client=client, tts_client=tts)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert tts.scripts == [PODCAST_OUT["script"]]
    podcast = Podcast.objects.get(note=note)
    assert podcast.script == PODCAST_OUT["script"]
    assert podcast.title == PODCAST_OUT["title"]
    assert podcast.duration_seconds > 0
    assert podcast.tts_provider == "fake"
    assert podcast.audio.name.startswith(f"podcasts/{user.user_id}/{note.pk}/")
    assert podcast.audio.name.endswith(".mp3")
    with podcast.audio.open("rb") as f:
        head = f.read(2)
    assert head[0] == 0xFF and (head[1] & 0xE0) == 0xE0  # MPEG frame sync


def test_tts_failure_fails_job_with_tts_code(note, user):
    from notes.models import Podcast
    from notes.tts.fake import FakeTTSClient

    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["podcast"])
    client = FakeClient(responses={OutputType.PODCAST: PODCAST_OUT})
    tts = FakeTTSClient(error=RuntimeError("voice service down"))
    run_generation_job(job.pk, client=client, tts_client=tts)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_TTS
    assert not Podcast.objects.filter(note=note).exists()


def test_invalid_podcast_script_fails_after_retry(note, user):
    job = GenerationJob.objects.create(note=note, owner=user, requested_outputs=["podcast"])
    monologue = {"title": "t", "script": "Alex: talking to myself"}
    client = FakeClient(
        script=[{OutputType.PODCAST: monologue}, {OutputType.PODCAST: monologue}]
    )
    run_generation_job(job.pk, client=client)
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_INVALID_OUTPUT


def _topics_for(notes):
    return {
        "topics": [
            {
                "name": "Routing",
                "priority": 1,
                "suggested_minutes": 90,
                "source_note_ids": [notes[0].pk],
            },
            {
                "name": "Dispatch flows",
                "priority": 2,
                "suggested_minutes": 60,
                "source_note_ids": [n.pk for n in notes],
            },
        ]
    }


def _plan_with_notes(user, contents):
    from notes.models import StudyPlan

    notes = []
    for i, body in enumerate(contents):
        note = Note(owner=user, original_filename=f"n{i}.docx", size_bytes=len(body))
        note.file.save(f"n{i}.docx", ContentFile(body), save=True)
        notes.append(note)
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set(notes)
    return plan, notes


class PerFileConverter:
    def __init__(self, failing=None):
        self._failing = failing

    def to_markdown(self, file_bytes, filename):
        from notes.convert.base import ConversionError

        if filename == self._failing:
            raise ConversionError("no extractable text")
        return f"content of {filename}"


def test_study_plan_job_combines_notes_and_persists_topics(user):
    plan, notes = _plan_with_notes(user, [b"PK\x03\x04 a", b"PK\x03\x04 b"])
    topics = _topics_for(notes)
    job = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    client = FakeClient(responses={OutputType.STUDY_PLAN: topics})
    run_generation_job(job.pk, client=client, markdown_converter=PerFileConverter())
    job.refresh_from_db()
    plan.refresh_from_db()
    assert job.status == GenerationJob.DONE
    document = client.document_text_seen[0]
    # headers carry the note id so the model can cite sources unambiguously
    assert f"# Note {notes[0].pk}: n0.docx" in document and "content of n0.docx" in document
    assert f"# Note {notes[1].pk}: n1.docx" in document and "content of n1.docx" in document
    assert plan.topics == topics["topics"]
    assert plan.topics[0]["source_note_ids"] == [notes[0].pk]
    assert plan.generated_at is not None
    assert plan.prompt_version == PROMPT_VERSION


def test_study_plan_rejects_hallucinated_source_ids(user):
    plan, notes = _plan_with_notes(user, [b"PK\x03\x04 a"])
    bad = {
        "topics": [
            {"name": "x", "priority": 1, "suggested_minutes": 30, "source_note_ids": [999999]}
        ]
    }
    job = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    client = FakeClient(script=[{OutputType.STUDY_PLAN: bad}, {OutputType.STUDY_PLAN: bad}])
    run_generation_job(job.pk, client=client, markdown_converter=PerFileConverter())
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_INVALID_OUTPUT
    assert "source_note_ids" in job.failure_message


def test_study_plan_context_uses_course_and_term_end(user):
    from courses.models import StudentCourse
    from institutions.models import Institution
    from users.models import StudentProfile

    institution = Institution.objects.create(
        name="Academia University",
        web_pages=["https://academia.example"],
        domains=["academia.example"],
        country="Kenya",
    )
    student = StudentProfile.objects.create(user=user, student_id="student-002")
    course = StudentCourse.objects.create(
        student=student,
        institution=institution,
        code="ACS 400",
        title="Computer Science Project",
        term_end_date="2026-12-15",
    )
    plan, notes = _plan_with_notes(user, [b"PK\x03\x04 a"])
    plan.course = course
    plan.save()
    job = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    client = FakeClient(responses={OutputType.STUDY_PLAN: _topics_for(notes)})
    run_generation_job(job.pk, client=client, markdown_converter=PerFileConverter())
    _, context = client.calls[0]
    assert context.course_name == "Computer Science Project"
    assert context.course_code == "ACS 400"
    assert context.term_end == "2026-12-15"


def test_study_plan_conversion_failure_names_the_note(user):
    plan, _ = _plan_with_notes(user, [b"PK\x03\x04 a", b"PK\x03\x04 b"])
    job = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    client = FakeClient()
    run_generation_job(
        job.pk, client=client, markdown_converter=PerFileConverter(failing="n1.docx")
    )
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_CONVERSION
    assert "n1.docx" in job.failure_message
    assert client.calls == []


def test_study_plan_combined_markdown_cap_applies(user, settings):
    settings.NOTES_MAX_MARKDOWN_CHARS = 30
    plan, _ = _plan_with_notes(user, [b"PK\x03\x04 a", b"PK\x03\x04 b"])
    job = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    run_generation_job(job.pk, client=FakeClient(), markdown_converter=PerFileConverter())
    job.refresh_from_db()
    assert job.status == GenerationJob.FAILED
    assert job.failure_code == GenerationJob.FAILURE_CONVERSION


def test_regenerating_replaces_topics_in_place(user):
    plan, notes = _plan_with_notes(user, [b"PK\x03\x04 a"])
    job1 = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    run_generation_job(
        job1.pk,
        client=FakeClient(responses={OutputType.STUDY_PLAN: _topics_for(notes)}),
        markdown_converter=PerFileConverter(),
    )
    new_topics = {
        "topics": [
            {
                "name": "Only one",
                "priority": 1,
                "suggested_minutes": 30,
                "source_note_ids": [notes[0].pk],
            }
        ]
    }
    job2 = GenerationJob.objects.create(
        owner=user, study_plan=plan, requested_outputs=["study_plan"]
    )
    run_generation_job(
        job2.pk,
        client=FakeClient(responses={OutputType.STUDY_PLAN: new_topics}),
        markdown_converter=PerFileConverter(),
    )
    plan.refresh_from_db()
    assert plan.topics == new_topics["topics"]


def test_worker_task_runs_job(job, settings):
    settings.AI_LLM_BACKEND = "fake"
    from notes.tasks import run_generation

    run_generation.delay(job.pk)
    job.refresh_from_db()
    assert job.status == GenerationJob.DONE
    assert job.note.summaries.exists()
