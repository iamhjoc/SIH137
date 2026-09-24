"""
Optimization job lifecycle: creation (with feasibility pre-check +
idempotency), state machine transitions, and route persistence.

Async functions (`*_async`) are used by the FastAPI layer.
Sync functions are used by the Celery worker (see app/db/sync_session.py)
to avoid mixing async/await inside a Celery task.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InfeasibleProblemError,
    OptimizationJobNotFoundError,
    ValidationAppError,
)
from app.db.models.customer import Customer
from app.db.models.depot import Depot
from app.db.models.optimization import JOB_TRANSITIONS, OptimizationJob
from app.db.models.route import RoutePlan, RouteStop, VehicleRoute
from app.db.models.vehicle import Vehicle
from app.graph.loader import load_graph_from_storage
from app.optimization.interfaces import OptimizationProblem, OptimizationResult
from app.optimization.validation import check_feasibility
from app.services.graph_service import get_graph_version
from app.services.traffic_service import get_traffic_scenario


async def create_optimization_job(
    db: AsyncSession, project_id: UUID, graph_version_id: UUID, traffic_scenario_id: UUID | None,
    algorithm: str, seed: int, objective_weights: dict, algorithm_config: dict, constraints: dict,
    idempotency_key: str | None = None, request_id: str | None = None,
) -> OptimizationJob:
    if idempotency_key:
        result = await db.execute(
            select(OptimizationJob).where(
                OptimizationJob.project_id == project_id,
                OptimizationJob.idempotency_key == idempotency_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing  # replay: return the existing job instead of creating a duplicate

    graph_version = await get_graph_version(db, graph_version_id)
    if graph_version is None or graph_version.project_id != project_id:
        raise ValidationAppError("graph_version_id must belong to the same project.")

    traffic_valid = True
    if traffic_scenario_id:
        scenario = await get_traffic_scenario(db, traffic_scenario_id)
        traffic_valid = scenario is not None and scenario.project_id == project_id
        if not traffic_valid:
            raise ValidationAppError("traffic_scenario_id must belong to the same project.")

    customers_result = await db.execute(select(Customer).where(Customer.project_id == project_id, Customer.status == "active"))
    customers = customers_result.scalars().all()
    vehicles_result = await db.execute(select(Vehicle).where(Vehicle.project_id == project_id, Vehicle.status == "active"))
    vehicles = vehicles_result.scalars().all()

    g = load_graph_from_storage(graph_version.storage_uri)
    # Resolve each vehicle's OWN start/end depot graph node -- the seeded
    # fleet alternates between two depots, so using vehicles[0]'s depot
    # for every vehicle (the old behavior) silently mis-costs and can
    # mis-flag as unreachable any route whose vehicle starts elsewhere.
    depot_ids = {v.start_depot_id for v in vehicles} | {v.end_depot_id for v in vehicles}
    depots_by_id: dict[UUID, Depot] = {}
    for depot_id in depot_ids:
        depot = await db.get(Depot, depot_id)
        if depot is not None:
            depots_by_id[depot_id] = depot
    depot_node = depots_by_id[vehicles[0].start_depot_id].graph_node_id if vehicles and vehicles[0].start_depot_id in depots_by_id else None

    feasibility = check_feasibility(
        customers=[{"id": str(c.id), "graph_node_id": c.graph_node_id, "demand_units": c.demand_units} for c in customers],
        vehicles=[{
            "id": str(v.id), "capacity_units": v.capacity_units,
            "start_depot_id": v.start_depot_id, "end_depot_id": v.end_depot_id,
            "start_depot_node": depots_by_id[v.start_depot_id].graph_node_id if v.start_depot_id in depots_by_id else None,
            "end_depot_node": depots_by_id[v.end_depot_id].graph_node_id if v.end_depot_id in depots_by_id else None,
        } for v in vehicles],
        graph=g,
        depot_node=depot_node or "",
        objective_weights=objective_weights,
        traffic_scenario_valid=traffic_valid,
    )
    if not feasibility.feasible:
        raise InfeasibleProblemError(details={"errors": feasibility.errors})

    job = OptimizationJob(
        project_id=project_id, graph_version_id=graph_version_id, traffic_scenario_id=traffic_scenario_id,
        algorithm=algorithm, seed=seed, objective_weights=objective_weights,
        algorithm_config=algorithm_config, constraints=constraints,
        idempotency_key=idempotency_key, status="queued", request_id=request_id,
    )
    db.add(job)
    await db.flush()
    return job


async def get_job(db: AsyncSession, organization_id: UUID, job_id: UUID) -> OptimizationJob:
    """Loads a job and verifies its project belongs to the caller's
    organization -- previously this endpoint accepted any job_id and
    never checked organization_id, breaking tenant isolation (any org
    could read/cancel/rerun any other org's optimization jobs)."""
    job = await db.get(OptimizationJob, job_id)
    if job is None:
        raise OptimizationJobNotFoundError()
    from app.services import project_service
    await project_service.get_project(db, organization_id, job.project_id)
    return job


async def list_jobs(db: AsyncSession, organization_id: UUID, project_id: UUID, limit: int = 50) -> list[OptimizationJob]:
    """Most-recent-first job history for a project -- used by the Overview
    KPI (active job count) and the Decision History page. Reuses
    get_project's org-ownership check so a caller can't list another
    org's jobs by guessing a project_id, same as every other project-
    scoped list endpoint in this codebase."""
    from app.services import project_service
    await project_service.get_project(db, organization_id, project_id)
    result = await db.execute(
        select(OptimizationJob)
        .where(OptimizationJob.project_id == project_id)
        .order_by(OptimizationJob.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def transition_job(db: AsyncSession, organization_id: UUID, job_id: UUID, new_status: str) -> OptimizationJob:
    job = await get_job(db, organization_id, job_id)
    if new_status not in JOB_TRANSITIONS.get(job.status, set()):
        raise ValidationAppError(f"Cannot transition optimization job from '{job.status}' to '{new_status}'.")
    job.status = new_status
    await db.flush()
    return job


async def cancel_job(db: AsyncSession, organization_id: UUID, job_id: UUID) -> OptimizationJob:
    return await transition_job(db, organization_id, job_id, "cancelled")


async def rerun_job(db: AsyncSession, organization_id: UUID, job_id: UUID) -> OptimizationJob:
    """A rerun always creates a brand new job; the original is left untouched."""
    original = await get_job(db, organization_id, job_id)
    return await create_optimization_job(
        db, original.project_id, original.graph_version_id, original.traffic_scenario_id,
        original.algorithm, original.seed, original.objective_weights, original.algorithm_config,
        original.constraints, idempotency_key=None, request_id=None,
    )


# ---------------------------------------------------------------------------
# Sync helpers used by the Celery worker (app/workers/optimization_worker.py)
# ---------------------------------------------------------------------------

def load_job_sync(job_id: UUID) -> OptimizationJob:
    from app.db.sync_session import get_sync_session
    session = get_sync_session()
    try:
        job = session.get(OptimizationJob, job_id)
        if job is None:
            raise OptimizationJobNotFoundError()
        session.expunge(job)
        return job
    finally:
        session.close()


def mark_job_running(job_id: UUID) -> None:
    from app.db.sync_session import get_sync_session
    session = get_sync_session()
    try:
        job = session.get(OptimizationJob, job_id)
        if job and job.status in JOB_TRANSITIONS and "running" in JOB_TRANSITIONS[job.status]:
            job.status = "running"
            session.commit()
    finally:
        session.close()


def mark_job_succeeded(job_id: UUID, best_cost: float) -> None:
    from app.db.sync_session import get_sync_session
    session = get_sync_session()
    try:
        job = session.get(OptimizationJob, job_id)
        if job:
            job.status = "succeeded"
            job.best_cost = best_cost
            session.commit()
    finally:
        session.close()


def mark_job_failed(job_id: UUID, error_message: str) -> None:
    from app.db.sync_session import get_sync_session
    session = get_sync_session()
    try:
        job = session.get(OptimizationJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = error_message[:1000]
            session.commit()
    finally:
        session.close()


def build_problem_from_job(job: OptimizationJob) -> OptimizationProblem:
    """Sync reconstruction of the OptimizationProblem for the worker process."""
    from app.db.sync_session import get_sync_session
    session = get_sync_session()
    try:
        from app.db.models.graph import GraphVersion
        from app.db.models.traffic import TrafficEdge

        graph_version = session.get(GraphVersion, job.graph_version_id)
        g = load_graph_from_storage(graph_version.storage_uri)

        customers = session.query(Customer).filter(Customer.project_id == job.project_id, Customer.status == "active").all()
        vehicles = session.query(Vehicle).filter(Vehicle.project_id == job.project_id, Vehicle.status == "active").all()

        # Resolve each vehicle's OWN start/end depot graph node -- the
        # seeded fleet alternates between two depots, so using
        # vehicles[0]'s depot for every vehicle mis-costs and can
        # mis-flag as unreachable any route whose vehicle starts
        # elsewhere (see fitness.evaluate / repair.repair_connectivity,
        # which now read start_depot_node/end_depot_node per vehicle).
        depot_ids = {v.start_depot_id for v in vehicles} | {v.end_depot_id for v in vehicles}
        depots_by_id = {}
        for depot_id in depot_ids:
            depot_row = session.get(Depot, depot_id)
            if depot_row is not None:
                depots_by_id[depot_id] = depot_row
        depot = depots_by_id.get(vehicles[0].start_depot_id) if vehicles else None
        end_depot = depots_by_id.get(vehicles[0].end_depot_id) if vehicles else None

        traffic_lookup: dict[tuple[str, str], dict[str, float]] = {}
        if job.traffic_scenario_id:
            rows = session.query(TrafficEdge).filter(
                TrafficEdge.scenario_id == job.traffic_scenario_id, TrafficEdge.time_bucket == 8
            ).all()
            for row in rows:
                u, v = row.graph_edge_id.split("->")
                traffic_lookup[(u, v)] = {"speed_kmh": row.speed_kmh, "congestion_factor": row.congestion_factor}

        return OptimizationProblem(
            graph=g,
            depot_node=depot.graph_node_id if depot else next(iter(g.nodes)),
            end_depot_node=end_depot.graph_node_id if end_depot else (depot.graph_node_id if depot else next(iter(g.nodes))),
            customers=[{"id": str(c.id), "graph_node_id": c.graph_node_id, "demand_units": c.demand_units,
                        "service_seconds": c.service_seconds} for c in customers],
            vehicles=[{
                "id": str(v.id), "capacity_units": v.capacity_units, "fixed_cost": v.fixed_cost,
                "cost_per_km": v.cost_per_km, "start_depot_id": str(v.start_depot_id),
                "end_depot_id": str(v.end_depot_id),
                "start_depot_node": depots_by_id[v.start_depot_id].graph_node_id if v.start_depot_id in depots_by_id else None,
                "end_depot_node": depots_by_id[v.end_depot_id].graph_node_id if v.end_depot_id in depots_by_id else None,
            } for v in vehicles],
            traffic_edges=traffic_lookup,
            objective_weights=job.objective_weights,
            constraints=job.constraints,
            seed=job.seed,
        )
    finally:
        session.close()


def persist_route_result(job: OptimizationJob, result: OptimizationResult, problem: OptimizationProblem) -> None:
    """
    Persist the winning routes for a succeeded job: per-vehicle geometry
    (for map rendering), real distance/time/congestion costs derived from
    the graph + traffic scenario used for this run, and every stop
    (including the depot start/end legs) tied to its actual customer or
    depot record so the API can resolve coordinates for the map.
    """
    import networkx as nx
    from geoalchemy2.shape import from_shape
    from shapely.geometry import LineString

    from app.db.sync_session import get_sync_session
    from app.optimization.route_cost import LegCost, path_cost

    session = get_sync_session()
    try:
        plan = RoutePlan(
            optimization_job_id=job.id, project_id=job.project_id,
            objective_cost=result.best_cost,
        )
        session.add(plan)
        session.flush()

        vehicles = session.query(Vehicle).filter(Vehicle.project_id == job.project_id, Vehicle.status == "active").all()
        graph = problem.graph

        # Same per-vehicle depot resolution as build_problem_from_job --
        # persisted route geometry/cost must use each vehicle's own
        # depot, not problem.depot_node/end_depot_node (vehicles[0]'s).
        depot_ids = {v.start_depot_id for v in vehicles} | {v.end_depot_id for v in vehicles}
        depots_by_id = {}
        for depot_id in depot_ids:
            depot_row = session.get(Depot, depot_id)
            if depot_row is not None:
                depots_by_id[depot_id] = depot_row

        plan_distance = plan_time = plan_congestion = 0.0

        for seq, route in enumerate(result.routes):
            stop_order = route.get("stop_order", [])
            vehicle = vehicles[route["vehicle_index"] % len(vehicles)] if vehicles else None

            route_depot_node = (
                depots_by_id[vehicle.start_depot_id].graph_node_id
                if vehicle is not None and vehicle.start_depot_id in depots_by_id
                else problem.depot_node
            )
            route_end_depot_node = (
                depots_by_id[vehicle.end_depot_id].graph_node_id
                if vehicle is not None and vehicle.end_depot_id in depots_by_id
                else problem.end_depot_node
            )
            node_sequence = (
                [route_depot_node]
                + [problem.customers[c]["graph_node_id"] for c in stop_order]
                + [route_end_depot_node]
            )
            full_path: list[str] = []
            try:
                for u, v in zip(node_sequence[:-1], node_sequence[1:]):
                    segment = nx.shortest_path(graph, u, v, weight="length_m")
                    full_path.extend(segment[:-1])
                full_path.append(node_sequence[-1])
            except nx.NetworkXNoPath:
                full_path = [n for n in node_sequence if n is not None]

            cost = path_cost(graph, full_path, problem.traffic_edges) if len(full_path) > 1 else LegCost(0.0, 0.0, 0.0)
            geometry = (
                from_shape(LineString([(graph.nodes[n]["lon"], graph.nodes[n]["lat"]) for n in full_path]), srid=4326)
                if len(full_path) > 1
                else None
            )

            vroute = VehicleRoute(
                route_plan_id=plan.id, vehicle_id=vehicle.id if vehicle else None,
                sequence_no=seq, load_units=route.get("load_units", 0),
                distance_m=cost.distance_m, time_s=cost.travel_time_s, geometry=geometry,
            )
            session.add(vroute)
            session.flush()

            stop_seq = 0
            session.add(RouteStop(
                vehicle_route_id=vroute.id, sequence_no=stop_seq, stop_type="depot_start",
                depot_id=vehicle.start_depot_id if vehicle else None, eta_seconds=0.0,
            ))

            elapsed = 0.0
            for cust_idx in stop_order:
                stop_seq += 1
                cust = problem.customers[cust_idx]
                elapsed += cust.get("service_seconds", 0)
                session.add(RouteStop(
                    vehicle_route_id=vroute.id, sequence_no=stop_seq, stop_type="customer",
                    customer_id=UUID(cust["id"]), eta_seconds=elapsed,
                ))

            stop_seq += 1
            session.add(RouteStop(
                vehicle_route_id=vroute.id, sequence_no=stop_seq, stop_type="depot_end",
                depot_id=vehicle.end_depot_id if vehicle else None, eta_seconds=elapsed,
            ))

            plan_distance += cost.distance_m
            plan_time += cost.travel_time_s
            plan_congestion += cost.congestion_cost

        plan.total_distance_m = plan_distance
        plan.total_time_s = plan_time
        plan.congestion_cost = plan_congestion

        session.commit()
    finally:
        session.close()
