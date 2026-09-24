from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import ValidationAppError
from app.db.models.depot import Depot
from app.db.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse
from app.services import project_service
from app.services.audit_service import record_event

router = APIRouter(tags=["vehicles"])


@router.post("/projects/{project_id}/vehicles", response_model=VehicleResponse)
async def create_vehicle(
    project_id: UUID, payload: VehicleCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    await project_service.get_project(db, principal.organization_id, project_id)

    for depot_id in (payload.start_depot_id, payload.end_depot_id):
        depot = await db.get(Depot, depot_id)
        if depot is None or depot.project_id != project_id:
            raise ValidationAppError("start_depot_id/end_depot_id must belong to the same project.")

    vehicle = Vehicle(
        project_id=project_id, code=payload.code, capacity_units=payload.capacity_units,
        fixed_cost=payload.fixed_cost, cost_per_km=payload.cost_per_km,
        max_route_seconds=payload.max_route_seconds,
        start_depot_id=payload.start_depot_id, end_depot_id=payload.end_depot_id, status="active",
    )
    db.add(vehicle)
    await db.flush()
    await record_event(db, principal.organization_id, "CREATE_VEHICLE", user_id=principal.user_id,
                        resource_type="vehicle", resource_id=str(vehicle.id))
    return vehicle


@router.get("/projects/{project_id}/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(project_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    await project_service.get_project(db, principal.organization_id, project_id)
    result = await db.execute(select(Vehicle).where(Vehicle.project_id == project_id))
    return list(result.scalars().all())
