"""Celery background tasks for dataset generation and comparative evaluation."""

from celery import shared_task

from .models import GenerationJob
from .services import execute_generation_job, run_comparative_evaluation


@shared_task(bind=True)
def run_generation_experiment_task(self, job_id: str) -> str:
    job = GenerationJob.objects.get(id=job_id)
    execute_generation_job(job)
    return str(job.id)


@shared_task(bind=True)
def run_comparative_evaluation_task(self) -> int:
    results = run_comparative_evaluation()
    return len(results)
