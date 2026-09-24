from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import NotFoundError
from app.services import project_service, traffic_service
from app.services.audit_service import record_event

settings = get_settings()
router = APIRouter(prefix="/traffic", tags=["traffic"])


class TrafficScenarioCreate(BaseModel):
    project_id: UUID
    graph_version_id: UUID
    name: str
    seed: int = settings.default_seed


class LiveTrafficScenarioCreate(BaseModel):
    project_id: UUID
    graph_version_id: UUID
    name: str = "Live Traffic"


@router.post("/scenarios")
async def create_scenario(
    payload: TrafficScenarioCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    """Deterministic synthetic traffic -- no API key required."""
    await project_service.get_project(db, principal.organization_id, payload.project_id)
    scenario = await traffic_service.create_simulated_traffic_scenario(
        db, payload.project_id, payload.graph_version_id, payload.name, payload.seed
    )
    await record_event(db, principal.organization_id, "CREATE_TRAFFIC_SCENARIO", user_id=principal.user_id,
                        resource_type="traffic_scenario", resource_id=str(scenario.id))
    return scenario


@router.post("/scenarios/live")
async def create_live_scenario(
    payload: LiveTrafficScenarioCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    """
    Pulls real current traffic from whichever provider is set via
    TRAFFIC_PROVIDER in your .env (tomtom | here | mappls). Fails with a
    clear validation error if TRAFFIC_API_KEY isn't configured.
    """
    await project_service.get_project(db, principal.organization_id, payload.project_id)
    scenario = await traffic_service.create_live_traffic_scenario(
        db, payload.project_id, payload.graph_version_id, payload.name
    )
    await record_event(db, principal.organization_id, "CREATE_TRAFFIC_SCENARIO", user_id=principal.user_id,
                        resource_type="traffic_scenario", resource_id=str(scenario.id),
                        metadata={"kind": "provider"})
    return scenario


@router.get("/scenarios")
async def list_scenarios(project_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    await project_service.get_project(db, principal.organization_id, project_id)
    from sqlalchemy import select

    from app.db.models.traffic import TrafficScenario
    result = await db.execute(select(TrafficScenario).where(TrafficScenario.project_id == project_id))
    return list(result.scalars().all())


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    scenario = await traffic_service.get_traffic_scenario(db, scenario_id)
    if scenario is None:
        raise NotFoundError("Traffic scenario not found.")
    await project_service.get_project(db, principal.organization_id, scenario.project_id)
    return scenario


@router.get("/scenarios/{scenario_id}/edges")
async def get_scenario_edges(
    scenario_id: UUID, time_bucket: int = 0,
    db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal),
):
    """Per-edge speed/congestion for one time bucket -- used by the Network
    map to color road segments by congestion instead of defaulting to 1
    (green) for every edge."""
    scenario = await traffic_service.get_traffic_scenario(db, scenario_id)
    if scenario is None:
        raise NotFoundError("Traffic scenario not found.")
    await project_service.get_project(db, principal.organization_id, scenario.project_id)
    return await traffic_service.list_scenario_edges(db, scenario_id, time_bucket)
