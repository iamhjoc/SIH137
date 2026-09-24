"""
Celery application. Optimization and benchmark work always runs here --
never inline inside a FastAPI request handler.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sih26137",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.optimization_worker", "app.workers.benchmark_worker", "app.workers.graph_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
)
