from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GraphVersionResponse(BaseModel):
    """Public shape of a GraphVersion -- deliberately omits `storage_uri`,
    which is a server-local filesystem path (e.g. `/tmp/objstore/...` or
    `/data/object-storage/...` for the filesystem backend) or an internal
    S3 key, neither of which a client has any use for and which leaks
    details of the server's storage layout."""
    id: UUID
    project_id: UUID
    version_no: int
    source: str
    node_count: int
    edge_count: int
    is_connected: bool
    status: str
    meta: dict
    created_at: datetime

    model_config = {"from_attributes": True}
