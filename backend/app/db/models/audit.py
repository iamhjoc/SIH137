import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin

AUDIT_EVENT_TYPES = (
    "LOGIN", "CREATE_PROJECT", "UPDATE_PROJECT", "CREATE_CUSTOMER", "IMPORT_CUSTOMERS",
    "CREATE_VEHICLE", "CREATE_GRAPH", "CREATE_TRAFFIC_SCENARIO", "CREATE_OPTIMIZATION_JOB",
    "CANCEL_OPTIMIZATION_JOB", "RERUN_OPTIMIZATION_JOB", "CREATE_BENCHMARK",
    "EXPORT_RESULT", "ADMIN_ACTION",
)


class AuditEvent(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "audit_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Never store passwords/tokens/secrets here.
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
