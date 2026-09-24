"""Normalizes traffic rows fetched from the DB into the
(u, v) -> {speed_kmh, congestion_factor} lookup used by route_cost.py."""
from __future__ import annotations


def normalize(rows: list[dict], time_bucket: int) -> dict[tuple[str, str], dict[str, float]]:
    lookup: dict[tuple[str, str], dict[str, float]] = {}
    for row in rows:
        if row["time_bucket"] != time_bucket:
            continue
        u, v = row["graph_edge_id"].split("->")
        lookup[(u, v)] = {"speed_kmh": row["speed_kmh"], "congestion_factor": row["congestion_factor"]}
    return lookup
