"""
Sync SQLAlchemy session for Celery workers (Celery tasks are sync by
default; using a sync engine here avoids event-loop conflicts with async
code running inside worker processes).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True, future=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)


def get_sync_session() -> Session:
    return SyncSessionLocal()
