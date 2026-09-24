"""Lightweight in-memory traffic value objects used by the optimization engine."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficFactor:
    graph_edge_id: str
    time_bucket: int
    speed_kmh: float
    congestion_factor: float
    confidence: float
