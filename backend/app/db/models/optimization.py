import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin

# Explicit allowed state machine transitions (see docs / section 23).
JOB_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled"},
    "running": {"succeeded", "failed", "cancelled"},
    "succeeded": {"completed"},
    "failed": set(),
    "cancelled": set(),
    "completed": set(),
}


class OptimizationJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "optimization_jobs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    graph_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_versions.id"), nullable=False
    )
    traffic_scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traffic_scenarios.id"), nullable=True
    )
    algorithm: Mapped[str] = mapped_column(String(30), nullable=False, default="qpso")
    algorithm_version: Mapped[str] = mapped_column(String(30), nullable=False, default="qpso-1.0.0")
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    algorithm_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    constraints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    best_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OptimizationIteration(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "optimization_iterations"

    optimization_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("optimization_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    iteration_no: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    best_cost: Mapped[float] = mapped_column(Float, nullable=False)
    mean_cost: Mapped[float] = mapped_column(Float, nullable=False)
    diversity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
