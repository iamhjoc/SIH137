from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import NotFoundError
from app.schemas.graph import GraphVersionResponse
from app.services import graph_service, project_service
from app.services.audit_service import record_event

settings = get_settings()
router = APIRouter(prefix="/graphs", tags=["graphs"])


class GraphImportRequest(BaseModel):
    project_id: UUID
    seed: int = settings.default_seed
    rows: int = 10
    cols: int = 10


class GraphBoundingBox(BaseModel):
    north: float
    south: float
    east: float
    west: float


class OsmGraphImportRequest(BaseModel):
    project_id: UUID
    place_name: str | None = Field(None, examples=["Chandigarh, India"])
    bbox: GraphBoundingBox | None = Field(
        None, description="Recommended for large metros (e.g. Delhi) to keep the graph demo-scale."
    )
    network_type: str = "drive"


@router.post("/import", response_model=GraphVersionResponse)
async def import_graph(
    payload: GraphImportRequest, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    """
    Deterministic synthetic grid graph (section 19) -- useful for tests,
    demos without network access, and QPSO benchmarking at a known size.
    For real city data use POST /graphs/import-osm instead.
    """
    await project_service.get_project(db, principal.organization_id, payload.project_id)
    graph_version = await graph_service.create_synthetic_graph_version(
        db, payload.project_id, payload.seed, payload.rows, payload.cols
    )
    await record_event(db, principal.organization_id, "CREATE_GRAPH", user_id=principal.user_id,
                        resource_type="graph_version", resource_id=str(graph_version.id))
    return graph_version


@router.post("/import-osm", response_model=GraphVersionResponse)
async def import_osm_graph(
    payload: OsmGraphImportRequest, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    """
    Real road network from OpenStreetMap via OSMnx/Overpass. Requires
    outbound network access from the API/worker process to Overpass (or
    OSM_OVERPASS_URL if you've configured a mirror) -- see .env.example.
    Provide `bbox` instead of `place_name` for large metros to keep the
    import demo-scale.
    """
    await project_service.get_project(db, principal.organization_id, payload.project_id)
    graph_version = await graph_service.create_osm_graph_version(
        db, payload.project_id,
        place_name=payload.place_name,
        bbox=payload.bbox.model_dump() if payload.bbox else None,
        network_type=payload.network_type,
    )
    await record_event(db, principal.organization_id, "CREATE_GRAPH", user_id=principal.user_id,
                        resource_type="graph_version", resource_id=str(graph_version.id),
                        metadata={"place_name": payload.place_name, "source": "osm"})
    return graph_version


@router.get("/{graph_id}", response_model=GraphVersionResponse)
async def get_graph(graph_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    graph_version = await graph_service.get_graph_version(db, graph_id)
    if graph_version is None:
        raise NotFoundError("Graph version not found.")
    await project_service.get_project(db, principal.organization_id, graph_version.project_id)
    return graph_version


@router.get("/{graph_id}/topology")
async def get_graph_topology(graph_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    """
    The actual node/edge topology (coordinates + lengths), separate from
    the lightweight GraphVersion metadata returned by GET /{graph_id} --
    this is what the frontend map needs to draw the network and is not
    cheap enough to inline into every metadata response.
    """
    graph_version = await graph_service.get_graph_version(db, graph_id)
    if graph_version is None:
        raise NotFoundError("Graph version not found.")
    await project_service.get_project(db, principal.organization_id, graph_version.project_id)

    g = graph_service.load_networkx_graph(graph_version)
    return {
        "graph_version_id": str(graph_id),
        "nodes": [
            {"id": node_id, "lat": data["lat"], "lon": data["lon"]}
            for node_id, data in g.nodes(data=True)
        ],
        "edges": [
            {"u": u, "v": v, "length_m": data.get("length_m"), "speed_kmh": data.get("speed_kmh")}
            for u, v, data in g.edges(data=True)
        ],
    }


@router.post("/{graph_id}/validate")
async def validate_graph(graph_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    graph_version = await graph_service.get_graph_version(db, graph_id)
    if graph_version is None:
        raise NotFoundError("Graph version not found.")
    await project_service.get_project(db, principal.organization_id, graph_version.project_id)

    from app.workers.graph_worker import validate_graph_version
    validate_graph_version.delay(str(graph_id))
    return {"status": "validation_queued", "graph_version_id": str(graph_id)}
