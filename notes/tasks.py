import time

from celery import shared_task

from .llm.base import LLMProviderError
from .models import GenerationJob
from .services.generation import run_generation_job


@shared_task
def health_check():
    return "ok"


# One initial attempt plus one retry per backoff step (~70s in total): long
# enough to ride out a provider 503 wave, short enough to stay inside the
# task's hard time limit.
PROVIDER_BACKOFF_SECONDS = (10, 20, 40)


# Hard limit so a hung provider call cannot pin a worker; soft limit gives
# the task a window to mark the job failed before the kill.
@shared_task(bind=True, soft_time_limit=270, time_limit=300)
def run_generation(self, job_id):
    for backoff in (*PROVIDER_BACKOFF_SECONDS, None):
        try:
            run_generation_job(job_id)
            return
        except LLMProviderError as exc:
            error = exc
            if backoff is None:
                break
            # Eager mode runs inside the HTTP request (tests, local dev);
            # sleeping there would hang the request, so only workers back off.
            if not self.request.is_eager:
                time.sleep(backoff)
    _mark_provider_failure(job_id, str(error))


def _mark_provider_failure(job_id, message):
    job = GenerationJob.objects.filter(pk=job_id).first()
    if job and job.status not in (GenerationJob.DONE, GenerationJob.FAILED):
        job.mark_failed(GenerationJob.FAILURE_PROVIDER, message)
