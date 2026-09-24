from uuid import UUID

from pydantic import BaseModel


class VehicleCreate(BaseModel):
    code: str
    capacity_units: int
    fixed_cost: float = 0.0
    cost_per_km: float = 0.0
    max_route_seconds: int = 28800
    start_depot_id: UUID
    end_depot_id: UUID


class VehicleResponse(BaseModel):
    id: UUID
    project_id: UUID
    code: str
    capacity_units: int
    fixed_cost: float
    cost_per_km: float
    max_route_seconds: int
    start_depot_id: UUID
    end_depot_id: UUID
    status: str

    model_config = {"from_attributes": True}
