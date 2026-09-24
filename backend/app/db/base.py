"""
Declarative base + shared mixins (UUID PK, timestamptz audit columns).
Import every model module here so Alembic autogenerate can discover them.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PointLocationMixin:
    """
    Mixin for models with a PostGIS POINT `location` column. Exposes plain
    `latitude`/`longitude` floats (decoded from the WKB geometry) so API
    response schemas can read them via `from_attributes` without every
    caller needing to know about geoalchemy2/shapely.
    """

    @property
    def longitude(self) -> float | None:
        if self.location is None:
            return None
        from geoalchemy2.shape import to_shape
        return to_shape(self.location).x

    @property
    def latitude(self) -> float | None:
        if self.location is None:
            return None
        from geoalchemy2.shape import to_shape
        return to_shape(self.location).y


# Import models so they register on Base.metadata for Alembic autogenerate.
from app.db.models import (  # noqa: F401
    audit,
    benchmark,
    customer,
    depot,
    graph,
    optimization,
    organization,
    project,
    route,
    traffic,
    user,
    vehicle,
)
