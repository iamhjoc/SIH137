"""Celery task for heavier graph import/validation work (OSMnx fetches, etc.)."""
from __future__ import annotations

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="graph.validate_version", bind=True)
def validate_graph_version(self, graph_version_id: str) -> dict:
    from app.services.graph_service import validate_and_persist_stats
    return validate_and_persist_stats(graph_version_id)
