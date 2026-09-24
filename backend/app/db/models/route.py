import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class RoutePlan(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "route_plans"

    optimization_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("optimization_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    total_distance_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_time_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    congestion_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    objective_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class VehicleRoute(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "vehicle_routes"

    route_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    geometry = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=True)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    time_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    load_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RouteStop(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "route_stops"

    vehicle_route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicle_routes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    depot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("depots.id"), nullable=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stop_type: Mapped[str] = mapped_column(String(20), nullable=False)  # depot_start|customer|depot_end
    eta_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class RouteLeg(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "route_legs"

    vehicle_route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicle_routes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    from_stop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_stops.id"), nullable=False
    )
    to_stop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_stops.id"), nullable=False
    )
    geometry = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=True)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    travel_time_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    congestion_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
