from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.organization import Organization


async def get_by_slug(db: AsyncSession, slug: str) -> Organization | None:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    return result.scalar_one_or_none()


async def create_organization(db: AsyncSession, name: str, slug: str) -> Organization:
    org = Organization(name=name, slug=slug)
    db.add(org)
    await db.flush()
    return org
