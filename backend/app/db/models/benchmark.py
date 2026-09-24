import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class BenchmarkExperiment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "benchmark_experiments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    graph_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_versions.id"), nullable=False
    )
    traffic_scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traffic_scenarios.id"), nullable=True
    )
    algorithms: Mapped[list] = mapped_column(JSONB, nullable=False)  # e.g. ["qpso","ga","aco"]
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")


class BenchmarkRun(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "benchmark_runs"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmark_experiments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    algorithm: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    repetition_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_cost: Mapped[float] = mapped_column(Float, nullable=False)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    travel_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_cost: Mapped[float] = mapped_column(Float, nullable=False)
    runtime_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    feasible: Mapped[bool] = mapped_column(nullable=False, default=True)
    iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
