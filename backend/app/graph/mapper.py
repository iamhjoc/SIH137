"""
Nearest-node mapping: map_coordinate_to_graph_node().
Object storage note: local dev uses the filesystem (see loader.py);
swap `save_graph_to_storage`/`load_graph_from_storage` for an S3-backed
implementation to move to production without touching callers.
"""
from __future__ import annotations

import math

import networkx as nx

from app.core.exceptions import CustomerGraphMappingError

MAX_MAPPING_DISTANCE_M = 500.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def map_coordinate_to_graph_node(
    g: nx.DiGraph, lat: float, lon: float, max_distance_m: float = MAX_MAPPING_DISTANCE_M
) -> str:
    best_node, best_dist = None, float("inf")
    for node_id, data in g.nodes(data=True):
        dist = _haversine_m(lat, lon, data["lat"], data["lon"])
        if dist < best_dist:
            best_node, best_dist = node_id, dist

    if best_node is None or best_dist > max_distance_m:
        raise CustomerGraphMappingError(
            details={"lat": lat, "lon": lon, "nearest_distance_m": best_dist, "max_distance_m": max_distance_m}
        )
    return best_node
