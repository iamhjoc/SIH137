"""
Project CRUD. Every query is scoped by organization_id -- this is where
multi-tenancy is enforced at the service layer (in addition to the
repository layer), per section 10.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, TenantIsolationError
from app.db.models.project import Project


async def create_project(db: AsyncSession, organization_id: UUID, name: str, timezone: str = "UTC") -> Project:
    project = Project(organization_id=organization_id, name=name, timezone=timezone, status="active")
    db.add(project)
    await db.flush()
    return project


async def list_projects(db: AsyncSession, organization_id: UUID, limit: int = 50, cursor: str | None = None) -> list[Project]:
    stmt = select(Project).where(Project.organization_id == organization_id).order_by(Project.created_at.desc()).limit(limit)
    if cursor:
        stmt = stmt.where(Project.id > cursor)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_project(db: AsyncSession, organization_id: UUID, project_id: UUID) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError("Project not found.")
    if project.organization_id != organization_id:
        raise TenantIsolationError()
    return project


async def update_project(db: AsyncSession, organization_id: UUID, project_id: UUID, **fields) -> Project:
    project = await get_project(db, organization_id, project_id)
    for key, value in fields.items():
        if value is not None:
            setattr(project, key, value)
    await db.flush()
    return project


async def delete_project(db: AsyncSession, organization_id: UUID, project_id: UUID) -> None:
    project = await get_project(db, organization_id, project_id)
    await db.delete(project)
    await db.flush()
