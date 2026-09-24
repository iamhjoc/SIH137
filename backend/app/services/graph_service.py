"""
Graph versioning: synthetic graph generation, storage, validation.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.graph import GraphVersion
from app.db.models.project import Project
from app.graph.loader import (
    generate_synthetic_grid_graph,
    import_graph_from_bbox,
    import_graph_from_place,
    load_graph_from_storage,
    save_graph_to_storage,
    validate_graph,
)


async def _next_version_no(db: AsyncSession, project_id: UUID) -> int:
    result = await db.execute(select(GraphVersion).where(GraphVersion.project_id == project_id).order_by(GraphVersion.version_no.desc()))
    last = result.scalars().first()
    return (last.version_no + 1) if last else 1


async def _set_default_if_unset(db: AsyncSession, project_id: UUID, graph_version_id: UUID) -> None:
    """A project's first graph version should become its default so
    depots/customers created afterward have something to map to --
    without this, default_graph_version_id stays null forever unless a
    caller remembers to set it explicitly (see the seed scripts)."""
    project = await db.get(Project, project_id)
    if project is not None and project.default_graph_version_id is None:
        project.default_graph_version_id = graph_version_id
        await db.flush()


async def create_synthetic_graph_version(db: AsyncSession, project_id: UUID, seed: int, rows: int = 10, cols: int = 10) -> GraphVersion:
    g = generate_synthetic_grid_graph(rows=rows, cols=cols, seed=seed)
    stats = validate_graph(g)
    version_no = await _next_version_no(db, project_id)

    storage_key = f"graphs/{project_id}/v{version_no}.json"
    storage_uri = save_graph_to_storage(g, storage_key)

    graph_version = GraphVersion(
        project_id=project_id,
        version_no=version_no,
        source="synthetic",
        storage_uri=storage_uri,
        node_count=stats["node_count"],
        edge_count=stats["edge_count"],
        is_connected=stats["is_connected"],
        status="ready",
        meta={"seed": seed, "rows": rows, "cols": cols},
    )
    db.add(graph_version)
    await db.flush()
    await _set_default_if_unset(db, project_id, graph_version.id)
    return graph_version


async def create_osm_graph_version(
    db: AsyncSession, project_id: UUID, place_name: str | None = None,
    bbox: dict[str, float] | None = None, network_type: str = "drive",
) -> GraphVersion:
    """
    Real road graph from OpenStreetMap via OSMnx. Provide either
    `place_name` (e.g. "Chandigarh, India") or `bbox`
    ({north, south, east, west}) -- bbox is recommended for large metros
    (Delhi) to keep the graph to a demo-scale zone rather than the whole
    municipal area. Immutable once created, same as the synthetic path --
    graph_versions are never edited in place, only superseded by a new
    version_no.
    """
    if bbox:
        g = import_graph_from_bbox(bbox["north"], bbox["south"], bbox["east"], bbox["west"], network_type)
        source_label = f"osm:bbox({bbox['north']:.4f},{bbox['south']:.4f},{bbox['east']:.4f},{bbox['west']:.4f})"
    elif place_name:
        g = import_graph_from_place(place_name, network_type)
        source_label = f"osm:place({place_name})"
    else:
        raise ValueError("Either place_name or bbox is required.")

    stats = validate_graph(g)
    version_no = await _next_version_no(db, project_id)

    storage_key = f"graphs/{project_id}/v{version_no}.json"
    storage_uri = save_graph_to_storage(g, storage_key)

    graph_version = GraphVersion(
        project_id=project_id,
        version_no=version_no,
        source="osm",
        storage_uri=storage_uri,
        node_count=stats["node_count"],
        edge_count=stats["edge_count"],
        is_connected=stats["is_connected"],
        status="ready" if stats["is_connected"] else "warning_disconnected",
        meta={"place_name": place_name, "bbox": bbox, "network_type": network_type, "source": source_label},
    )
    db.add(graph_version)
    await db.flush()
    await _set_default_if_unset(db, project_id, graph_version.id)
    return graph_version


async def get_graph_version(db: AsyncSession, graph_version_id: UUID) -> GraphVersion | None:
    result = await db.execute(select(GraphVersion).where(GraphVersion.id == graph_version_id))
    return result.scalar_one_or_none()


async def list_graph_versions(db: AsyncSession, project_id: UUID) -> list[GraphVersion]:
    result = await db.execute(
        select(GraphVersion).where(GraphVersion.project_id == project_id).order_by(GraphVersion.version_no.desc())
    )
    return list(result.scalars().all())


def load_networkx_graph(graph_version: GraphVersion):
    return load_graph_from_storage(graph_version.storage_uri)


def validate_and_persist_stats(graph_version_id: str) -> dict:
    """Sync entry point used by the Celery graph worker for heavier validation jobs."""
    from app.db.sync_session import get_sync_session
    session = get_sync_session()
    try:
        gv = session.get(GraphVersion, UUID(graph_version_id))
        if gv is None:
            return {"status": "not_found"}
        g = load_graph_from_storage(gv.storage_uri)
        stats = validate_graph(g)
        gv.node_count = stats["node_count"]
        gv.edge_count = stats["edge_count"]
        gv.is_connected = stats["is_connected"]
        gv.status = "ready" if stats["is_connected"] else "warning_disconnected"
        session.commit()
        return stats
    finally:
        session.close()
