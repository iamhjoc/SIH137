"""Traffic scenario creation (simulated or real-provider) and edge persistence."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.traffic import TrafficEdge, TrafficScenario
from app.graph.loader import load_graph_from_storage
from app.services.graph_service import get_graph_version
from app.traffic.adapters import get_traffic_adapter
from app.traffic.simulator import generate_traffic

settings = get_settings()


async def create_simulated_traffic_scenario(db: AsyncSession, project_id: UUID, graph_version_id: UUID, name: str, seed: int) -> TrafficScenario:
    """Deterministic synthetic traffic -- always available, no API key needed."""
    graph_version = await get_graph_version(db, graph_version_id)
    if graph_version is None or graph_version.project_id != project_id:
        raise ValueError("Graph version does not belong to this project.")

    g = load_graph_from_storage(graph_version.storage_uri)
    records = generate_traffic(g, seed)

    scenario = TrafficScenario(project_id=project_id, name=name, kind="simulated", seed=seed, status="ready")
    db.add(scenario)
    await db.flush()

    await _persist_edges(db, scenario.id, records)
    return scenario


async def create_live_traffic_scenario(db: AsyncSession, project_id: UUID, graph_version_id: UUID, name: str) -> TrafficScenario:
    """
    Real traffic pulled from whichever provider is configured via
    TRAFFIC_PROVIDER in .env (tomtom | here | mappls). Live providers
    return a single "current" reading rather than per-hour historical
    buckets, so this scenario's edges are all stored at time_bucket=0 --
    build_problem_from_job/load_traffic_lookup already query a single
    bucket, so nothing downstream needs to change; just don't mix a
    'live' scenario's bucket semantics with a 'simulated' one's 24-bucket
    day cycle in the same comparison.
    """
    graph_version = await get_graph_version(db, graph_version_id)
    if graph_version is None or graph_version.project_id != project_id:
        raise ValueError("Graph version does not belong to this project.")

    g = load_graph_from_storage(graph_version.storage_uri)
    adapter = get_traffic_adapter()
    records = await adapter.fetch(g, seed=0)

    scenario = TrafficScenario(project_id=project_id, name=name, kind="provider", seed=None, status="ready")
    db.add(scenario)
    await db.flush()

    await _persist_edges(db, scenario.id, records)
    return scenario


async def _persist_edges(db: AsyncSession, scenario_id: UUID, records: list[dict]) -> None:
    edges = [
        TrafficEdge(scenario_id=scenario_id, graph_edge_id=r["graph_edge_id"], time_bucket=r["time_bucket"],
                    speed_kmh=r["speed_kmh"], congestion_factor=r["congestion_factor"], confidence=r["confidence"])
        for r in records
    ]
    db.add_all(edges)
    await db.flush()


async def get_traffic_scenario(db: AsyncSession, scenario_id: UUID) -> TrafficScenario | None:
    result = await db.execute(select(TrafficScenario).where(TrafficScenario.id == scenario_id))
    return result.scalar_one_or_none()


async def load_traffic_lookup(db: AsyncSession, scenario_id: UUID, time_bucket: int) -> dict[tuple[str, str], dict[str, float]]:
    result = await db.execute(
        select(TrafficEdge).where(TrafficEdge.scenario_id == scenario_id, TrafficEdge.time_bucket == time_bucket)
    )
    lookup = {}
    for row in result.scalars().all():
        u, v = row.graph_edge_id.split("->")
        lookup[(u, v)] = {"speed_kmh": row.speed_kmh, "congestion_factor": row.congestion_factor}
    return lookup


async def list_scenario_edges(db: AsyncSession, scenario_id: UUID, time_bucket: int = 0) -> list[dict]:
    """Per-edge congestion/speed for one time bucket of a scenario, as a
    flat list the frontend map can consume directly (see NetworkMap /
    NetworkPage, which color roads by congestion_factor)."""
    result = await db.execute(
        select(TrafficEdge).where(TrafficEdge.scenario_id == scenario_id, TrafficEdge.time_bucket == time_bucket)
    )
    edges = []
    for row in result.scalars().all():
        u, v = row.graph_edge_id.split("->")
        edges.append({
            "u": u, "v": v,
            "speed_kmh": row.speed_kmh,
            "congestion_factor": row.congestion_factor,
        })
    return edges
