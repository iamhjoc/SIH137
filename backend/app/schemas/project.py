from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    timezone: str = "UTC"


class ProjectUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    timezone: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    default_graph_version_id: UUID | None
    timezone: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
