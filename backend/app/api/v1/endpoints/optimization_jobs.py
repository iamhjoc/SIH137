"""
POST /optimization-jobs, GET /{id}, POST /{id}/cancel, GET /{id}/progress,
GET /{id}/routes, POST /{id}/rerun.

Optimization NEVER runs inline: creation validates + persists the job then
queues a Celery task; the worker performs queued -> running -> succeeded.
"""
import json
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import NotFoundError
from app.schemas.optimization import (
    OptimizationJobCreate,
    OptimizationJobResponse,
    OptimizationProgressResponse,
)
from app.services import optimization_service, route_service
from app.services.audit_service import record_event

settings = get_settings()
# async client -- get_progress below is an `async def` FastAPI handler, and
# the sync redis.Redis client used to block the event loop on every call.
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

router = APIRouter(prefix="/optimization-jobs", tags=["optimization"])


@router.post("", response_model=OptimizationJobResponse)
async def create_job(
    payload: OptimizationJobCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER", "DISPATCHER")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_request_id: str | None = Header(default=None),
):
    job = await optimization_service.create_optimization_job(
        db, payload.project_id, payload.graph_version_id, payload.traffic_scenario_id,
        payload.algorithm, payload.seed, payload.objective_weights.model_dump(),
        payload.algorithm_config.model_dump(), payload.constraints.model_dump(),
        idempotency_key=idempotency_key, request_id=x_request_id,
    )
    await record_event(db, principal.organization_id, "CREATE_OPTIMIZATION_JOB", user_id=principal.user_id,
                        resource_type="optimization_job", resource_id=str(job.id), request_id=x_request_id)

    # The job (and its audit event) must be committed before the worker
    # is queued -- .delay() can be picked up by a worker on a separate
    # connection almost immediately, and get_db_session's own commit only
    # runs after this handler returns, which would otherwise race the
    # worker's own SELECT for a job row that isn't visible yet.
    await db.commit()

    from app.workers.optimization_worker import run_optimization_job
    run_optimization_job.delay(str(job.id))

    return job


@router.get("/{job_id}", response_model=OptimizationJobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    return await optimization_service.get_job(db, principal.organization_id, job_id)


@router.get("", response_model=list[OptimizationJobResponse])
async def list_jobs(
    project_id: UUID, limit: int = 50,
    db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal),
):
    return await optimization_service.list_jobs(db, principal.organization_id, project_id, limit)


@router.post("/{job_id}/cancel", response_model=OptimizationJobResponse)
async def cancel_job(
    job_id: UUID, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER", "DISPATCHER")),
):
    job = await optimization_service.cancel_job(db, principal.organization_id, job_id)
    await record_event(db, principal.organization_id, "CANCEL_OPTIMIZATION_JOB", user_id=principal.user_id,
                        resource_type="optimization_job", resource_id=str(job.id))
    return job


@router.get("/{job_id}/progress", response_model=OptimizationProgressResponse)
async def get_progress(job_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    job = await optimization_service.get_job(db, principal.organization_id, job_id)
    raw = await redis_client.get(f"optimization_job:{job_id}:progress")
    if raw:
        data = json.loads(raw)
        return OptimizationProgressResponse(**data)
    return OptimizationProgressResponse(
        job_id=job_id, status=job.status, progress=0.0, iteration=0,
        total_iterations=job.algorithm_config.get("iterations", 0), best_cost=job.best_cost, elapsed_ms=0,
    )


@router.get("/{job_id}/routes")
async def get_routes(job_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    job = await optimization_service.get_job(db, principal.organization_id, job_id)
    plan = await route_service.get_route_plan_for_job(db, job_id)
    if plan is None:
        raise NotFoundError("No route plan exists yet for this optimization job.")

    vehicle_routes = await route_service.get_vehicle_routes(db, plan.id)
    routes = []
    for vr in vehicle_routes:
        stops = await route_service.get_route_stops(db, vr.id)
        stop_coords = await route_service.resolve_stop_coordinates(db, stops)
        routes.append({
            "vehicle_id": str(vr.vehicle_id) if vr.vehicle_id else None,
            "sequence_no": vr.sequence_no,
            "distance_m": vr.distance_m,
            "time_s": vr.time_s,
            "load_units": vr.load_units,
            "path": route_service.route_geometry_coordinates(vr),
            "stops": [
                {
                    "sequence_no": s.sequence_no,
                    "stop_type": s.stop_type,
                    "latitude": stop_coords.get(s.id, (None, None))[0],
                    "longitude": stop_coords.get(s.id, (None, None))[1],
                    "eta_seconds": s.eta_seconds,
                }
                for s in stops
            ],
        })

    return {
        "job_id": str(job_id),
        "status": job.status,
        "metrics": {
            "distance_m": plan.total_distance_m,
            "time_s": plan.total_time_s,
            "congestion_cost": plan.congestion_cost,
            "objective_cost": plan.objective_cost,
        },
        "routes": routes,
        "provenance": {
            "seed": job.seed,
            "graph_version": str(job.graph_version_id),
            "algorithm_version": job.algorithm_version,
        },
    }


@router.post("/{job_id}/rerun", response_model=OptimizationJobResponse)
async def rerun_job(
    job_id: UUID, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER", "DISPATCHER")),
):
    new_job = await optimization_service.rerun_job(db, principal.organization_id, job_id)
    await record_event(db, principal.organization_id, "RERUN_OPTIMIZATION_JOB", user_id=principal.user_id,
                        resource_type="optimization_job", resource_id=str(new_job.id))

    # See create_job above: commit before queuing so the worker doesn't
    # race an uncommitted job row.
    await db.commit()

    from app.workers.optimization_worker import run_optimization_job
    run_optimization_job.delay(str(new_job.id))

    return new_job
