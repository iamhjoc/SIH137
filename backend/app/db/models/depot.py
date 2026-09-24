import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PointLocationMixin, TimestampMixin, UUIDPKMixin


class Depot(Base, UUIDPKMixin, TimestampMixin, PointLocationMixin):
    __tablename__ = "depots"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location = mapped_column(Geometry(geometry_type="POINT", srid=4326,spatial_index=False), nullable=False)
    graph_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    open_time: Mapped[str | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[str | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
