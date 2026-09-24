from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    external_ref: str
    name: str
    # Provide EITHER (latitude, longitude) OR address -- if address is
    # given, the configured GEOCODING_PROVIDER resolves it server-side.
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    address: str | None = Field(None, examples=["123 Model Town, Ludhiana, Punjab"])
    demand_units: int = Field(1, ge=0)
    service_seconds: int = Field(300, ge=0)
    window_start: str | None = None
    window_end: str | None = None
    priority: int = 1


class CustomerImportRow(BaseModel):
    external_ref: str
    name: str
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    demand_units: int = 1
    service_seconds: int = 300
    window_start: str | None = None
    window_end: str | None = None
    priority: int = 1


class CustomerImportRequest(BaseModel):
    rows: list[CustomerImportRow]
    graph_version_id: UUID  # used to nearest-node-map each imported customer


class CustomerImportRowResult(BaseModel):
    external_ref: str
    status: str  # "created" | "rejected"
    reason: str | None = None


class CustomerImportResult(BaseModel):
    created: int
    rejected: int
    results: list[CustomerImportRowResult]


class CustomerResponse(BaseModel):
    id: UUID
    project_id: UUID
    external_ref: str
    name: str
    latitude: float | None = None
    longitude: float | None = None
    demand_units: int
    status: str

    model_config = {"from_attributes": True}
