"""
Celery task that performs the queued -> running -> succeeded/failed
transition and executes the QPSO (or requested algorithm) engine.

Flow (per section 24):
  Validate request -> Create DB job -> Queue worker task -> Return job_id
  -> Worker picks job -> queued->running -> QPSO -> Persist progress
  -> Persist route -> succeeded
"""
from __future__ import annotations

import json
from uuid import UUID

import redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.optimization.interfaces import IterationRecord, RoutingAlgorithm
from app.optimization.qpso import QPSOConfig, QPSOEngine
from app.workers.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _progress_key(job_id: str) -> str:
    return f"optimization_job:{job_id}:progress"


def _build_engine(algorithm: str, algorithm_config: dict) -> RoutingAlgorithm:
    """Dispatch by job.algorithm instead of always building QPSOEngine --
    the frontend's algorithm picker (GA/ACO/PSO/Dijkstra/A*) previously
    had no effect because every job ran QPSO regardless of this field."""
    import inspect

    from app.benchmarks.algorithms import ALGORITHM_REGISTRY

    name = (algorithm or "qpso").lower()
    if name == "qpso":
        return QPSOEngine(QPSOConfig(**(algorithm_config or {})))

    algo_cls = ALGORITHM_REGISTRY.get(name)
    if algo_cls is None:
        raise ValueError(f"Unknown optimization algorithm: {algorithm!r}")

    # The baseline algorithms (GA/ACO/PSO/Dijkstra/A*) each take their own
    # constructor kwargs, not QPSOConfig's shape -- forward only the keys
    # that exist on this algorithm's __init__ so a QPSO-shaped
    # algorithm_config (currently the only shape AlgorithmConfig sends,
    # see app/schemas/optimization.py) doesn't raise a TypeError; anything
    # not recognized falls back to that algorithm's own tuned default.
    valid_keys = set(inspect.signature(algo_cls.__init__).parameters) - {"self"}
    kwargs = {k: v for k, v in (algorithm_config or {}).items() if k in valid_keys}
    return algo_cls(**kwargs)


@celery_app.task(name="optimization.run_job", bind=True)
def run_optimization_job(self, job_id: str) -> dict:
    """
    NOTE: This task is deliberately decoupled from the async SQLAlchemy
    session used by FastAPI (Celery workers use a sync engine/session --
    see app/services/optimization_service.py for the sync repository used
    here in a full implementation). This stub focuses on demonstrating the
    correct state machine + QPSO execution + Redis progress contract; wire
    it to a sync SQLAlchemy session factory before production use.
    """
    from app.services.optimization_service import (
        build_problem_from_job,
        load_job_sync,
        mark_job_failed,
        mark_job_running,
        mark_job_succeeded,
        persist_route_result,
    )

    job = load_job_sync(UUID(job_id))
    mark_job_running(job.id)

    def progress_callback(record: IterationRecord):
        payload = {
            "job_id": job_id,
            "status": "running",
            "progress": min(record.iteration_no / max(job.algorithm_config.get("iterations", 500), 1), 1.0),
            "iteration": record.iteration_no,
            "total_iterations": job.algorithm_config.get("iterations", 500),
            "best_cost": record.best_cost,
            "elapsed_ms": record.elapsed_ms,
        }
        redis_client.set(_progress_key(job_id), json.dumps(payload), ex=3600)

    try:
        problem = build_problem_from_job(job)
        engine = _build_engine(job.algorithm, job.algorithm_config)
        result = engine.optimize(problem, progress_callback=progress_callback)

        if not result.feasible:
            mark_job_failed(job.id, "Optimization did not converge to a feasible solution.")
            return {"status": "failed"}

        persist_route_result(job, result, problem)
        mark_job_succeeded(job.id, result.best_cost)
        return {"status": "succeeded", "best_cost": result.best_cost}

    except Exception as exc:
        logger.exception("optimization_job_failed", job_id=job_id)
        mark_job_failed(job.id, str(exc))
        return {"status": "failed", "error": str(exc)}
