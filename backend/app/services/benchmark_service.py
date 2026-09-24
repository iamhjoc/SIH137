"""Benchmark experiment orchestration."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.benchmark import BenchmarkExperiment, BenchmarkRun


async def create_experiment(
    db: AsyncSession, project_id: UUID, name: str, graph_version_id: UUID,
    traffic_scenario_id: UUID | None, algorithms: list[str], repetitions: int, seed: int,
) -> BenchmarkExperiment:
    experiment = BenchmarkExperiment(
        project_id=project_id, name=name, graph_version_id=graph_version_id,
        traffic_scenario_id=traffic_scenario_id, algorithms=algorithms,
        repetitions=repetitions, seed=seed, status="queued",
    )
    db.add(experiment)
    await db.flush()
    return experiment


async def get_experiment(db: AsyncSession, experiment_id: UUID) -> BenchmarkExperiment | None:
    result = await db.execute(select(BenchmarkExperiment).where(BenchmarkExperiment.id == experiment_id))
    return result.scalar_one_or_none()


async def list_experiments(db: AsyncSession, project_id: UUID, limit: int = 50) -> list[BenchmarkExperiment]:
    result = await db.execute(
        select(BenchmarkExperiment)
        .where(BenchmarkExperiment.project_id == project_id)
        .order_by(BenchmarkExperiment.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_runs(db: AsyncSession, experiment_id: UUID) -> list[BenchmarkRun]:
    result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.experiment_id == experiment_id))
    return list(result.scalars().all())


def execute_experiment(experiment_id: str) -> dict:
    """Sync entry point invoked by the Celery benchmark worker."""
    from app.benchmarks.runner import run_experiment, summarize
    from app.db.models.customer import Customer
    from app.db.models.depot import Depot
    from app.db.models.graph import GraphVersion
    from app.db.models.vehicle import Vehicle
    from app.db.sync_session import get_sync_session
    from app.graph.loader import load_graph_from_storage
    from app.optimization.interfaces import OptimizationProblem

    session = get_sync_session()
    try:
        experiment = session.get(BenchmarkExperiment, UUID(experiment_id))
        if experiment is None:
            return {"status": "not_found"}
        experiment.status = "running"
        session.commit()

        graph_version = session.get(GraphVersion, experiment.graph_version_id)
        g = load_graph_from_storage(graph_version.storage_uri)
        customers = session.query(Customer).filter(Customer.project_id == experiment.project_id, Customer.status == "active").all()
        vehicles = session.query(Vehicle).filter(Vehicle.project_id == experiment.project_id, Vehicle.status == "active").all()
        depot = session.get(Depot, vehicles[0].start_depot_id) if vehicles else None

        problem = OptimizationProblem(
            graph=g,
            depot_node=depot.graph_node_id if depot else next(iter(g.nodes)),
            end_depot_node=depot.graph_node_id if depot else next(iter(g.nodes)),
            customers=[{"id": str(c.id), "graph_node_id": c.graph_node_id, "demand_units": c.demand_units,
                        "service_seconds": c.service_seconds} for c in customers],
            vehicles=[{"id": str(v.id), "capacity_units": v.capacity_units, "fixed_cost": v.fixed_cost,
                       "cost_per_km": v.cost_per_km} for v in vehicles],
            traffic_edges={},
            objective_weights={"distance": 0.25, "time": 0.4, "congestion": 0.25, "late": 0.1},
            constraints={},
            seed=experiment.seed,
        )

        results = run_experiment(problem, experiment.algorithms, experiment.repetitions, experiment.seed)

        for alg, samples in results.items():
            for i, sample in enumerate(samples):
                session.add(BenchmarkRun(
                    experiment_id=experiment.id, algorithm=alg, repetition_no=i,
                    seed=experiment.seed + i, objective_cost=sample.objective_cost,
                    distance_m=sample.distance_m, travel_time_s=sample.travel_time_s,
                    congestion_cost=sample.congestion_cost, runtime_ms=sample.runtime_ms,
                    feasible=sample.feasible, iterations=sample.iterations,
                ))

        experiment.status = "completed"
        session.commit()
        return summarize(results)
    finally:
        session.close()
