"""
Shortest-path helpers over NetworkX, hiding NetworkX specifics from services.
"""
from __future__ import annotations

import networkx as nx


def shortest_path(g: nx.DiGraph, source: str, target: str, weight: str = "length_m") -> list[str]:
    return nx.shortest_path(g, source, target, weight=weight)


def shortest_distance(g: nx.DiGraph, source: str, target: str) -> float:
    return nx.shortest_path_length(g, source, target, weight="length_m")


def shortest_time(g: nx.DiGraph, source: str, target: str) -> float:
    def time_weight(u, v, d):
        speed = d.get("speed_kmh", 40.0)
        return (d.get("length_m", 0.0) / 1000.0) / max(speed, 1.0) * 3600.0

    return nx.shortest_path_length(g, source, target, weight=time_weight)
