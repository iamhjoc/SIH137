import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Vehicle(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("project_id", "code", name="uq_vehicles_project_code"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    fixed_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_per_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_route_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=28800)
    start_depot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("depots.id"), nullable=False
    )
    end_depot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("depots.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
