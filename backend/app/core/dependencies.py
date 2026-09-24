"""
FastAPI dependencies: DB session, current principal, RBAC role guards.

Authentication has been removed from this application. There is no login,
no token, and no user-supplied credential of any kind -- every request is
treated as a single default admin principal, scoped to a default
organization that is auto-provisioned on first use.

Multi-tenancy note: `get_current_principal` returns a principal carrying
organization_id. Every repository/service call MUST be scoped using
that organization_id -- this file is the single choke point through
which tenant context enters the request pipeline.
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.session import get_db_session

ROLE_HIERARCHY = ["VIEWER", "ANALYST", "DISPATCHER", "MANAGER", "ADMIN"]

# Fixed, well-known IDs for the single default org/user every request is
# attributed to now that login has been removed. Auto-provisioned lazily
# below so the app works against a fresh database with no seed step.
DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str


async def get_db(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return session


async def _ensure_default_principal_exists(db: AsyncSession) -> None:
    """Idempotently create the default organization/user rows if they're
    not already there. Safe to call on every request; on conflict this is
    a no-op."""
    await db.execute(
        pg_insert(Organization)
        .values(
            id=DEFAULT_ORGANIZATION_ID,
            name="Default Organization",
            slug="default",
            status="active",
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await db.execute(
        pg_insert(User)
        .values(
            id=DEFAULT_USER_ID,
            organization_id=DEFAULT_ORGANIZATION_ID,
            email="system@local",
            full_name="System",
            hashed_password="!login-disabled!",
            role="ADMIN",
            is_active=True,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await db.flush()


async def get_current_principal(db: AsyncSession = Depends(get_db)) -> Principal:
    await _ensure_default_principal_exists(db)
    return Principal(
        user_id=DEFAULT_USER_ID,
        organization_id=DEFAULT_ORGANIZATION_ID,
        role="ADMIN",
    )


def require_role(*allowed_roles: str):
    """
    Usage: Depends(require_role("admin", "manager"))
    Role comparison is case-insensitive; the highest-privilege roles
    implicitly satisfy checks for lower ones is NOT assumed -- roles
    must be explicitly listed to keep authorization intent obvious.
    """
    allowed_upper = {r.upper() for r in allowed_roles}

    async def _dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role.upper() not in allowed_upper:
            raise ForbiddenError(
                f"Role '{principal.role}' is not permitted; requires one of {sorted(allowed_upper)}."
            )
        return principal

    return _dependency


async def get_request_id(x_request_id: str | None = Header(default=None)) -> str:
    return x_request_id or ""
