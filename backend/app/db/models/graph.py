import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class GraphVersion(Base, UUIDPKMixin, TimestampMixin):
    """
    Immutable graph version. The actual node/edge payload is stored in
    object storage (see app/graph/loader.py); this row stores metadata,
    stats and the storage pointer.
    """
    __tablename__ = "graph_versions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="synthetic")
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_connected: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
