import dataclasses
import logging
import time

from django.conf import settings
from django.core.files.base import ContentFile

from ..convert.base import ConversionError
from ..llm.base import (
    PROMPT_VERSION,
    DocumentSource,
    GenerationContext,
    OutputType,
    validate_podcast_script,
    validate_questions,
    validate_study_plan,
    validate_summary,
)
from django.utils import timezone

from ..models import GenerationJob, Podcast, QuestionSet, Summary

logger = logging.getLogger("professor")


def get_llm_client():
    if settings.AI_LLM_BACKEND == "fake":
        from ..llm.fake import FakeClient

        return FakeClient()
    from ..llm.gemini import GeminiClient

    return GeminiClient(api_key=settings.GEMINI_API_KEY)


def get_markdown_converter():
    from ..convert.markitdown import MarkItDownConverter

    return MarkItDownConverter()


def get_tts_client():
    if settings.AI_TTS_BACKEND == "fake":
        from ..tts.fake import FakeTTSClient

        return FakeTTSClient()
    from ..tts.gemini import GeminiTTSClient

    return GeminiTTSClient(api_key=settings.GEMINI_API_KEY)


def _context_for(job):
    if job.study_plan is not None:
        course = job.study_plan.course
        if course:
            return GenerationContext(
                course_name=course.title,
                course_code=course.code or "",
                term_end=str(course.term_end_date) if course.term_end_date else "",
            )
        return GenerationContext()
    note = job.note
    if note.course:
        return GenerationContext(
            course_name=note.course.title,
            course_code=note.course.code,
            question_format=job.question_format,
        )
    return GenerationContext(
        course_name=note.course_label, question_format=job.question_format
    )


def _validate_outputs(result, output_types, question_format, valid_note_ids=None):
    problems = []
    if OutputType.SUMMARY in output_types:
        summary_problems = validate_summary(result.outputs.get(OutputType.SUMMARY))
        problems.extend(f"summary: {p}" for p in summary_problems)
    if OutputType.QUESTIONS in output_types:
        question_problems = validate_questions(
            result.outputs.get(OutputType.QUESTIONS), question_format
        )
        problems.extend(f"questions: {p}" for p in question_problems)
    if OutputType.PODCAST in output_types:
        podcast_problems = validate_podcast_script(result.outputs.get(OutputType.PODCAST))
        problems.extend(f"podcast: {p}" for p in podcast_problems)
    if OutputType.STUDY_PLAN in output_types:
        plan_problems = validate_study_plan(
            result.outputs.get(OutputType.STUDY_PLAN), valid_note_ids=valid_note_ids
        )
        problems.extend(f"study_plan: {p}" for p in plan_problems)
    return problems


def _markdown_for(note, markdown_converter):
    with note.file.open("rb") as f:
        source_bytes = f.read()
    markdown_converter = markdown_converter or get_markdown_converter()
    markdown = markdown_converter.to_markdown(source_bytes, note.original_filename)
    if len(markdown) > settings.NOTES_MAX_MARKDOWN_CHARS:
        raise ConversionError("Converted document exceeds the Markdown input limit.")
    return markdown


def _document_for_plan(plan, markdown_converter):
    # Study plans need text from every note; a scanned note has no markdown to
    # contribute, so the job fails naming it rather than planning around a gap.
    sections = []
    for note in plan.notes.order_by("pk"):
        if note.converted_markdown:
            markdown = note.converted_markdown
        else:
            try:
                markdown = _markdown_for(note, markdown_converter)
            except ConversionError as exc:
                raise ConversionError(f"{note.original_filename}: {exc}") from exc
            note.converted_markdown = markdown
            note.save(update_fields=["converted_markdown"])
        sections.append(f"# Note {note.pk}: {note.original_filename}\n\n{markdown}")
    combined = "\n\n---\n\n".join(sections)
    if len(combined) > settings.NOTES_MAX_MARKDOWN_CHARS:
        raise ConversionError("Combined notes exceed the Markdown input limit.")
    return DocumentSource(markdown=combined)


def _document_for(note, markdown_converter):
    if note.converted_markdown:
        return DocumentSource(markdown=note.converted_markdown)
    try:
        markdown = _markdown_for(note, markdown_converter)
    except ConversionError as exc:
        # Scanned/image PDFs yield no usable text; Gemini reads them natively.
        if not note.file.name.lower().endswith(".pdf"):
            raise
        logger.warning(
            "note %s markdown extraction failed (%s); falling back to native pdf", note.pk, exc
        )
        with note.file.open("rb") as f:
            return DocumentSource(pdf_bytes=f.read())
    note.converted_markdown = markdown
    note.save(update_fields=["converted_markdown"])
    return DocumentSource(markdown=markdown)


def run_generation_job(job_id, client=None, markdown_converter=None, tts_client=None):
    job = (
        GenerationJob.objects.select_related(
            "note", "note__course", "study_plan", "study_plan__course"
        )
        .filter(pk=job_id)
        .first()
    )
    if job is None or job.status in (GenerationJob.DONE, GenerationJob.FAILED):
        logger.warning("generation job %s skipped (missing or already finished)", job_id)
        return
    job.mark_processing()
    job.prompt_version = PROMPT_VERSION
    job.save(update_fields=["prompt_version"])

    try:
        if job.study_plan is not None:
            document = _document_for_plan(job.study_plan, markdown_converter)
        else:
            document = _document_for(job.note, markdown_converter)
    except ConversionError as exc:
        _fail(job, GenerationJob.FAILURE_CONVERSION, str(exc))
        return
    except (OSError, ValueError) as exc:
        _fail(job, GenerationJob.FAILURE_FILE_UNREADABLE, str(exc))
        return

    client = client or get_llm_client()
    output_types = [OutputType(o) for o in job.requested_outputs]
    context = _context_for(job)
    valid_note_ids = (
        set(job.study_plan.notes.values_list("pk", flat=True)) if job.study_plan else None
    )

    input_tokens = output_tokens = 0
    started = time.monotonic()
    for attempt in range(2):
        try:
            result = client.generate(document, output_types, context)
        except Exception as exc:
            _fail(job, GenerationJob.FAILURE_PROVIDER, str(exc))
            return
        input_tokens += result.input_tokens
        output_tokens += result.output_tokens
        problems = _validate_outputs(result, output_types, job.question_format, valid_note_ids)
        if not problems:
            break
        if attempt == 0:
            context = dataclasses.replace(context, corrective_note="; ".join(problems))
    else:
        _fail(job, GenerationJob.FAILURE_INVALID_OUTPUT, "; ".join(problems))
        return

    if OutputType.SUMMARY in output_types:
        Summary.objects.create(
            note=job.note,
            job=job,
            content=result.outputs[OutputType.SUMMARY],
            prompt_version=PROMPT_VERSION,
        )
    if OutputType.QUESTIONS in output_types:
        QuestionSet.objects.create(
            note=job.note,
            job=job,
            format=job.question_format,
            questions=result.outputs[OutputType.QUESTIONS],
            prompt_version=PROMPT_VERSION,
        )
    if OutputType.PODCAST in output_types:
        script_data = result.outputs[OutputType.PODCAST]
        tts_client = tts_client or get_tts_client()
        try:
            tts_result = tts_client.synthesize(script_data["script"])
        except Exception as exc:
            _fail(job, GenerationJob.FAILURE_TTS, str(exc))
            return
        podcast = Podcast(
            note=job.note,
            job=job,
            title=script_data.get("title", ""),
            script=script_data["script"],
            duration_seconds=tts_result.duration_seconds,
            tts_provider=tts_client.provider,
            prompt_version=PROMPT_VERSION,
        )
        podcast.audio.save("episode.mp3", ContentFile(tts_result.audio_mp3), save=True)
        logger.info(
            "podcast tts job=%s note=%s provider=%s seconds=%.1f audio_tokens=%s",
            job.pk,
            job.note_id,
            tts_client.provider,
            tts_result.duration_seconds,
            tts_result.audio_tokens,
        )
    if OutputType.STUDY_PLAN in output_types:
        plan = job.study_plan
        plan.topics = result.outputs[OutputType.STUDY_PLAN]["topics"]
        plan.generated_at = timezone.now()
        plan.prompt_version = PROMPT_VERSION
        plan.save(update_fields=["topics", "generated_at", "prompt_version"])
    job.mark_done(input_tokens=input_tokens, output_tokens=output_tokens)
    logger.info(
        "generation job %s done note=%s owner=%s tokens_in=%s tokens_out=%s latency=%.1fs",
        job.pk,
        job.note_id,
        job.owner_id,
        input_tokens,
        output_tokens,
        time.monotonic() - started,
    )


def _fail(job, code, message):
    job.mark_failed(code, message)
    logger.error(
        "generation job %s failed note=%s owner=%s code=%s: %s",
        job.pk,
        job.note_id,
        job.owner_id,
        code,
        message,
    )
