from datetime import time
from uuid import UUID

from pydantic import BaseModel, Field


class DepotCreate(BaseModel):
    name: str = Field(..., examples=["Central Depot"])
    # Provide EITHER (latitude, longitude) OR address (geocoded server-side
    # via the configured GEOCODING_PROVIDER).
    latitude: float | None = Field(None, ge=-90, le=90, examples=[30.9010])
    longitude: float | None = Field(None, ge=-180, le=180, examples=[75.8573])
    address: str | None = Field(None, examples=["Sector 17, Chandigarh"])
    graph_version_id: UUID | None = Field(
        None, description="Used to nearest-node-map this depot. Falls back to the project's default_graph_version_id if omitted."
    )
    open_time: time | None = None
    close_time: time | None = None


class DepotResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    latitude: float | None = None
    longitude: float | None = None
    open_time: time | None = None
    close_time: time | None = None
    status: str

    model_config = {"from_attributes": True}
