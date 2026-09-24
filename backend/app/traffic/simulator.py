"""
Deterministic simulated traffic generator: per edge, per time bucket,
speed / congestion factor / confidence -- reproducible given a fixed seed.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

TIME_BUCKETS_PER_DAY = 24  # 1-hour buckets; index = hour of day


def generate_traffic(g: nx.DiGraph, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    records = []

    for u, v, data in g.edges(data=True):
        free_flow_speed = data.get("speed_kmh", 40.0)
        edge_id = f"{u}->{v}"
        # Each edge gets a fixed "busyness" profile, seeded, so re-running
        # with the same seed reproduces identical traffic.
        base_congestion = rng.uniform(0.5, 1.0)

        for bucket in range(TIME_BUCKETS_PER_DAY):
            # Simple rush-hour shape: worse congestion 8-10 and 17-19.
            rush = 1.0
            if bucket in (8, 9, 17, 18):
                rush = 0.5
            elif bucket in (7, 10, 16, 19):
                rush = 0.75

            congestion_factor = float(np.clip(base_congestion * rush + rng.normal(0, 0.03), 0.15, 1.0))
            speed_kmh = float(max(free_flow_speed * congestion_factor, 5.0))

            records.append({
                "graph_edge_id": edge_id,
                "time_bucket": bucket,
                "speed_kmh": speed_kmh,
                "congestion_factor": congestion_factor,
                "confidence": 0.9,
            })

    return records
