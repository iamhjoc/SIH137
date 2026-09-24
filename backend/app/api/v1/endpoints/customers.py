from uuid import UUID

from fastapi import APIRouter, Depends
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Principal, get_current_principal, get_db, require_role
from app.core.exceptions import ValidationAppError
from app.db.models.customer import Customer
from app.geocoding.adapters import get_geocoding_adapter
from app.schemas.customer import (
    CustomerCreate,
    CustomerImportRequest,
    CustomerImportResult,
    CustomerImportRowResult,
    CustomerResponse,
)
from app.services import graph_service, project_service
from app.services.audit_service import record_event

router = APIRouter(tags=["customers"])


async def _resolve_coordinates(payload: CustomerCreate) -> tuple[float, float]:
    """Either the request already has lat/lon, or an address that needs
    geocoding via the configured GEOCODING_PROVIDER (see .env.example)."""
    if payload.latitude is not None and payload.longitude is not None:
        return payload.latitude, payload.longitude
    if payload.address:
        result = await get_geocoding_adapter().geocode(payload.address)
        return result.latitude, result.longitude
    raise ValidationAppError("Provide either (latitude, longitude) or an address.")


@router.post("/projects/{project_id}/customers", response_model=CustomerResponse)
async def create_customer(
    project_id: UUID, payload: CustomerCreate, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER", "DISPATCHER")),
):
    await project_service.get_project(db, principal.organization_id, project_id)
    latitude, longitude = await _resolve_coordinates(payload)

    customer = Customer(
        project_id=project_id, external_ref=payload.external_ref, name=payload.name,
        location=from_shape(Point(longitude, latitude), srid=4326),
        demand_units=payload.demand_units, service_seconds=payload.service_seconds,
        window_start=payload.window_start, window_end=payload.window_end,
        priority=payload.priority, status="active",
    )
    db.add(customer)
    await db.flush()
    await record_event(db, principal.organization_id, "CREATE_CUSTOMER", user_id=principal.user_id,
                        resource_type="customer", resource_id=str(customer.id))
    return customer


@router.post("/projects/{project_id}/customers/import", response_model=CustomerImportResult)
async def import_customers(
    project_id: UUID, payload: CustomerImportRequest, db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("ADMIN", "MANAGER", "DISPATCHER")),
):
    """
    Bulk import: for each row, geocode (if no lat/lon given) -> validate
    -> nearest-node-map against `graph_version_id` -> insert. Rows that
    fail geocoding, mapping, or a duplicate external_ref are REJECTED
    individually rather than aborting the whole batch, so one bad address
    in a 500-row CSV doesn't block the other 499.
    """
    await project_service.get_project(db, principal.organization_id, project_id)
    graph_version = await graph_service.get_graph_version(db, payload.graph_version_id)
    if graph_version is None or graph_version.project_id != project_id:
        raise ValidationAppError("graph_version_id must belong to this project.")
    g = graph_service.load_networkx_graph(graph_version)

    existing_refs_result = await db.execute(select(Customer.external_ref).where(Customer.project_id == project_id))
    existing_refs = {row[0] for row in existing_refs_result.all()}
    seen_in_batch: set[str] = set()

    results: list[CustomerImportRowResult] = []
    created = 0

    for row in payload.rows:
        if row.external_ref in existing_refs or row.external_ref in seen_in_batch:
            results.append(CustomerImportRowResult(external_ref=row.external_ref, status="rejected", reason="Duplicate external_ref."))
            continue

        try:
            if row.latitude is not None and row.longitude is not None:
                latitude, longitude = row.latitude, row.longitude
            elif row.address:
                geocoded = await get_geocoding_adapter().geocode(row.address)
                latitude, longitude = geocoded.latitude, geocoded.longitude
            else:
                raise ValidationAppError("Row has neither coordinates nor an address.")

            from app.graph.mapper import map_coordinate_to_graph_node
            graph_node_id = map_coordinate_to_graph_node(g, latitude, longitude)

            customer = Customer(
                project_id=project_id, external_ref=row.external_ref, name=row.name,
                location=from_shape(Point(longitude, latitude), srid=4326),
                graph_node_id=graph_node_id, demand_units=row.demand_units, service_seconds=row.service_seconds,
                window_start=row.window_start, window_end=row.window_end, priority=row.priority, status="active",
            )
            db.add(customer)
            seen_in_batch.add(row.external_ref)
            created += 1
            results.append(CustomerImportRowResult(external_ref=row.external_ref, status="created"))
        except ValidationAppError as exc:
            results.append(CustomerImportRowResult(external_ref=row.external_ref, status="rejected", reason=exc.message))

    await db.flush()
    await record_event(db, principal.organization_id, "IMPORT_CUSTOMERS", user_id=principal.user_id,
                        resource_type="project", resource_id=str(project_id),
                        metadata={"created": created, "rejected": len(results) - created})

    return CustomerImportResult(created=created, rejected=len(results) - created, results=results)


@router.get("/projects/{project_id}/customers", response_model=list[CustomerResponse])
async def list_customers(
    project_id: UUID, limit: int = 50, cursor: str | None = None,
    db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_current_principal),
):
    await project_service.get_project(db, principal.organization_id, project_id)
    stmt = select(Customer).where(Customer.project_id == project_id).order_by(Customer.id).limit(limit)
    if cursor:
        stmt = stmt.where(Customer.id > cursor)
    result = await db.execute(stmt)
    return list(result.scalars().all())
