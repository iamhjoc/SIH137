"""Read-side access to persisted route plans/routes/stops for the API."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.customer import Customer
from app.db.models.depot import Depot
from app.db.models.route import RoutePlan, RouteStop, VehicleRoute


async def get_route_plan_for_job(db: AsyncSession, optimization_job_id: UUID) -> RoutePlan | None:
    result = await db.execute(select(RoutePlan).where(RoutePlan.optimization_job_id == optimization_job_id))
    return result.scalar_one_or_none()


async def get_vehicle_routes(db: AsyncSession, route_plan_id: UUID) -> list[VehicleRoute]:
    result = await db.execute(
        select(VehicleRoute).where(VehicleRoute.route_plan_id == route_plan_id).order_by(VehicleRoute.sequence_no)
    )
    return list(result.scalars().all())


async def get_route_stops(db: AsyncSession, vehicle_route_id: UUID) -> list[RouteStop]:
    result = await db.execute(
        select(RouteStop).where(RouteStop.vehicle_route_id == vehicle_route_id).order_by(RouteStop.sequence_no)
    )
    return list(result.scalars().all())


def route_geometry_coordinates(vehicle_route: VehicleRoute) -> list[list[float]]:
    """Decode a VehicleRoute's PostGIS LINESTRING into [[lon, lat], ...]."""
    if vehicle_route.geometry is None:
        return []
    from geoalchemy2.shape import to_shape
    return [[x, y] for x, y in to_shape(vehicle_route.geometry).coords]


async def resolve_stop_coordinates(
    db: AsyncSession, stops: list[RouteStop],
) -> dict[UUID, tuple[float | None, float | None]]:
    """
    Batch-resolve each stop's (latitude, longitude) from its linked
    customer or depot, keyed by RouteStop.id -- avoids an N+1 query per
    stop when a route has many customers.
    """
    customer_ids = {s.customer_id for s in stops if s.customer_id is not None}
    depot_ids = {s.depot_id for s in stops if s.depot_id is not None}

    customers: dict[UUID, Customer] = {}
    if customer_ids:
        result = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers = {c.id: c for c in result.scalars().all()}

    depots: dict[UUID, Depot] = {}
    if depot_ids:
        result = await db.execute(select(Depot).where(Depot.id.in_(depot_ids)))
        depots = {d.id: d for d in result.scalars().all()}

    coords: dict[UUID, tuple[float | None, float | None]] = {}
    for stop in stops:
        if stop.customer_id is not None and stop.customer_id in customers:
            c = customers[stop.customer_id]
            coords[stop.id] = (c.latitude, c.longitude)
        elif stop.depot_id is not None and stop.depot_id in depots:
            d = depots[stop.depot_id]
            coords[stop.id] = (d.latitude, d.longitude)
        else:
            coords[stop.id] = (None, None)
    return coords
