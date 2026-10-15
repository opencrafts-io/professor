from celery import shared_task

from .services.generation import run_generation_job


@shared_task
def health_check():
    return "ok"


# Hard limit so a hung provider call cannot pin a worker; soft limit gives
# the task a window to mark the job failed before the kill.
@shared_task(soft_time_limit=270, time_limit=300)
def run_generation(job_id):
    run_generation_job(job_id)
