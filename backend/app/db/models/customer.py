import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PointLocationMixin, TimestampMixin, UUIDPKMixin


class Customer(Base, UUIDPKMixin, TimestampMixin, PointLocationMixin):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("project_id", "external_ref", name="uq_customers_project_external_ref"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    external_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location = mapped_column(Geometry(geometry_type="POINT", srid=4326,spatial_index=False), nullable=False)
    graph_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    demand_units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    service_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    window_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    window_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
