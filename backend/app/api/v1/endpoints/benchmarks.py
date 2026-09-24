from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import NotFoundError
from app.services import benchmark_service, project_service
from app.services.audit_service import record_event

settings = get_settings()
router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


class BenchmarkCreate(BaseModel):
    project_id: UUID
    name: str
    graph_version_id: UUID
    traffic_scenario_id: UUID | None = None
    algorithms: list[str] = ["qpso", "ga", "aco", "pso", "dijkstra", "astar"]
    repetitions: int = 5
    seed: int = settings.default_seed


@router.post("")
async def create_benchmark(
    payload: BenchmarkCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER", "ANALYST")),
):
    await project_service.get_project(db, principal.organization_id, payload.project_id)
    experiment = await benchmark_service.create_experiment(
        db, payload.project_id, payload.name, payload.graph_version_id, payload.traffic_scenario_id,
        payload.algorithms, payload.repetitions, payload.seed,
    )
    await record_event(db, principal.organization_id, "CREATE_BENCHMARK", user_id=principal.user_id,
                        resource_type="benchmark_experiment", resource_id=str(experiment.id))

    from app.workers.benchmark_worker import run_benchmark_experiment
    run_benchmark_experiment.delay(str(experiment.id))

    return experiment


@router.get("/{experiment_id}")
async def get_benchmark(experiment_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    experiment = await benchmark_service.get_experiment(db, experiment_id)
    if experiment is None:
        raise NotFoundError("Benchmark experiment not found.")
    await project_service.get_project(db, principal.organization_id, experiment.project_id)
    runs = await benchmark_service.list_runs(db, experiment_id)

    # Group runs by algorithm and reduce each group with the existing
    # aggregate() helper (already implemented in app/benchmarks/metrics.py,
    # just never previously wired up to an endpoint) -- this is the same
    # AggregateMetrics shape the frontend's comparison table expects.
    from app.benchmarks.metrics import RunSample, aggregate
    by_algorithm: dict[str, list[RunSample]] = {}
    for run in runs:
        by_algorithm.setdefault(run.algorithm, []).append(RunSample(
            objective_cost=run.objective_cost, distance_m=run.distance_m,
            travel_time_s=run.travel_time_s, congestion_cost=run.congestion_cost,
            runtime_ms=run.runtime_ms, feasible=run.feasible, iterations=run.iterations,
        ))
    aggregates = {alg: aggregate(samples) for alg, samples in by_algorithm.items() if samples}

    return {"experiment": experiment, "runs": runs, "aggregates": aggregates}


@router.get("")
async def list_benchmarks(
    project_id: UUID, limit: int = 50,
    db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal),
):
    await project_service.get_project(db, principal.organization_id, project_id)
    return await benchmark_service.list_experiments(db, project_id, limit)
