import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class TrafficScenario(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "traffic_scenarios"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="simulated")  # static|simulated|provider
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ready")


class TrafficEdge(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "traffic_edges"
    __table_args__ = (
        UniqueConstraint(
            "scenario_id", "graph_edge_id", "time_bucket",
            name="uq_traffic_edges_scenario_edge_bucket",
        ),
    )

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traffic_scenarios.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    graph_edge_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    time_bucket: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # minutes-of-day bucket
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_factor: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1, 1 = free flow
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
