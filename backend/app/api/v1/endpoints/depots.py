from uuid import UUID

from fastapi import APIRouter, Depends
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.depot import Depot
from app.geocoding.adapters import get_geocoding_adapter
from app.schemas.depot import DepotCreate, DepotResponse
from app.services import project_service

router = APIRouter(tags=["depots"])


@router.post("/projects/{project_id}/depots", response_model=DepotResponse)
async def create_depot(
    project_id: UUID, payload: DepotCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    await project_service.get_project(db, principal.organization_id, project_id)

    if payload.latitude is not None and payload.longitude is not None:
        latitude, longitude = payload.latitude, payload.longitude
    elif payload.address:
        geocoded = await get_geocoding_adapter().geocode(payload.address)
        latitude, longitude = geocoded.latitude, geocoded.longitude
    else:
        raise ValidationAppError("Provide either (latitude, longitude) or an address.")

    graph_node_id = None
    project = await project_service.get_project(db, principal.organization_id, project_id)
    effective_graph_version_id = payload.graph_version_id or project.default_graph_version_id
    if effective_graph_version_id:
        from app.graph.mapper import map_coordinate_to_graph_node
        from app.services import graph_service
        graph_version = await graph_service.get_graph_version(db, effective_graph_version_id)
        if graph_version:
            g = graph_service.load_networkx_graph(graph_version)
            graph_node_id = map_coordinate_to_graph_node(g, latitude, longitude)

    depot = Depot(
        project_id=project_id, name=payload.name,
        location=from_shape(Point(longitude, latitude), srid=4326),
        graph_node_id=graph_node_id,
        open_time=payload.open_time, close_time=payload.close_time, status="active",
    )
    db.add(depot)
    await db.flush()
    return depot


@router.get("/projects/{project_id}/depots", response_model=list[DepotResponse])
async def list_depots(project_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    await project_service.get_project(db, principal.organization_id, project_id)
    result = await db.execute(select(Depot).where(Depot.project_id == project_id))
    return list(result.scalars().all())


@router.get("/depots/{depot_id}", response_model=DepotResponse)
async def get_depot(depot_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    depot = await db.get(Depot, depot_id)
    if depot is None:
        raise NotFoundError("Depot not found.")
    await project_service.get_project(db, principal.organization_id, depot.project_id)
    return depot
