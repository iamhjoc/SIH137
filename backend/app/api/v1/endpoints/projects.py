from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.schemas.graph import GraphVersionResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services import graph_service, project_service
from app.services.audit_service import record_event

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    project = await project_service.create_project(db, principal.organization_id, payload.name, payload.timezone)
    await record_event(db, principal.organization_id, "CREATE_PROJECT", user_id=principal.user_id,
                        resource_type="project", resource_id=str(project.id))
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    limit: int = 50, cursor: str | None = None,
    db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal),
):
    return await project_service.list_projects(db, principal.organization_id, limit, cursor)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    return await project_service.get_project(db, principal.organization_id, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID, payload: ProjectUpdate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER")),
):
    project = await project_service.update_project(db, principal.organization_id, project_id, **payload.model_dump())
    await record_event(db, principal.organization_id, "UPDATE_PROJECT", user_id=principal.user_id,
                        resource_type="project", resource_id=str(project.id))
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN")),
):
    await project_service.delete_project(db, principal.organization_id, project_id)


@router.get("/{project_id}/graphs", response_model=list[GraphVersionResponse])
async def list_project_graphs(
    project_id: UUID, db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal),
):
    """Version history for this project's road graph (section 21, Network Explorer)."""
    await project_service.get_project(db, principal.organization_id, project_id)
    return await graph_service.list_graph_versions(db, project_id)
