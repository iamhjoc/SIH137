"""Writes audit events. Never stores passwords/tokens/secrets in metadata."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditEvent

SENSITIVE_KEYS = {"password", "token", "access_token", "refresh_token", "secret", "hashed_password"}


def _scrub(metadata: dict) -> dict:
    return {k: v for k, v in metadata.items() if k.lower() not in SENSITIVE_KEYS}


async def record_event(
    db: AsyncSession, organization_id: UUID, event_type: str, user_id: UUID | None = None,
    resource_type: str | None = None, resource_id: str | None = None,
    request_id: str | None = None, metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        metadata_json=_scrub(metadata or {}),
    )
    db.add(event)
    await db.flush()
    return event
