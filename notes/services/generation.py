import dataclasses
import logging
import time

from django.conf import settings

from ..llm.base import PROMPT_VERSION, GenerationContext, OutputType, validate_summary
from ..models import GenerationJob, Summary

logger = logging.getLogger("professor")


def get_llm_client():
    if settings.AI_LLM_BACKEND == "fake":
        from ..llm.fake import FakeClient

        return FakeClient()
    from ..llm.gemini import GeminiClient

    return GeminiClient(api_key=settings.GEMINI_API_KEY)


def get_converter():
    if settings.AI_CONVERTER_BACKEND == "fake":
        from ..convert.fake import FakeConverter

        return FakeConverter()
    from ..convert.ilovepdf import ILovePDFConverter

    return ILovePDFConverter(public_key=settings.ILOVEAPI_PUBLIC_KEY)


def _context_for(note):
    if note.course:
        return GenerationContext(
            course_name=note.course.course_name, course_code=note.course.course_code
        )
    return GenerationContext(course_name=note.course_label)


def _validate_outputs(result, output_types):
    problems = []
    if OutputType.SUMMARY in output_types:
        summary_problems = validate_summary(result.outputs.get(OutputType.SUMMARY))
        problems.extend(f"summary: {p}" for p in summary_problems)
    return problems


def run_generation_job(job_id, client=None):
    job = GenerationJob.objects.select_related("note", "note__course").filter(pk=job_id).first()
    if job is None or job.status in (GenerationJob.DONE, GenerationJob.FAILED):
        logger.warning("generation job %s skipped (missing or already finished)", job_id)
        return
    job.mark_processing()
    job.prompt_version = PROMPT_VERSION
    job.save(update_fields=["prompt_version"])

    try:
        with job.note.file.open("rb") as f:
            pdf_bytes = f.read()
    except (OSError, ValueError) as exc:
        _fail(job, GenerationJob.FAILURE_FILE_UNREADABLE, str(exc))
        return

    client = client or get_llm_client()
    output_types = [OutputType(o) for o in job.requested_outputs]
    context = _context_for(job.note)

    input_tokens = output_tokens = 0
    started = time.monotonic()
    for attempt in range(2):
        try:
            result = client.generate(pdf_bytes, output_types, context)
        except Exception as exc:
            _fail(job, GenerationJob.FAILURE_PROVIDER, str(exc))
            return
        input_tokens += result.input_tokens
        output_tokens += result.output_tokens
        problems = _validate_outputs(result, output_types)
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
