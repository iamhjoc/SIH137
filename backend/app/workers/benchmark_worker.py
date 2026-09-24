"""Celery task that runs a full benchmark experiment across algorithms."""
from __future__ import annotations

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="benchmark.run_experiment", bind=True)
def run_benchmark_experiment(self, experiment_id: str) -> dict:
    from app.services.benchmark_service import execute_experiment
    return execute_experiment(experiment_id)
