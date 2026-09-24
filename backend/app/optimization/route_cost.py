"""
Per-leg route costing: distance, travel time (traffic-adjusted), congestion cost.
Never hard-codes a single value -- always derived from graph edge data and,
when available, the traffic scenario's speed/congestion for that edge+bucket.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass
class LegCost:
    distance_m: float
    travel_time_s: float
    congestion_cost: float


def leg_cost(graph: nx.DiGraph, u: str, v: str,
             traffic_edges: dict[tuple[str, str], dict[str, float]]) -> LegCost:
    edge = graph[u][v]
    distance_m = float(edge.get("length_m", 0.0))
    free_flow_speed = float(edge.get("speed_kmh", 40.0))

    traffic = traffic_edges.get((u, v))
    if traffic:
        traffic_speed = max(traffic.get("speed_kmh", free_flow_speed), 1.0)
        congestion_factor = traffic.get("congestion_factor", 1.0)
    else:
        traffic_speed = free_flow_speed
        congestion_factor = 1.0

    travel_time_s = (distance_m / 1000.0) / traffic_speed * 3600.0
    free_flow_time_s = (distance_m / 1000.0) / max(free_flow_speed, 1.0) * 3600.0
    congestion_cost = max(travel_time_s - free_flow_time_s, 0.0) * (1.0 / max(congestion_factor, 0.01))

    return LegCost(distance_m=distance_m, travel_time_s=travel_time_s, congestion_cost=congestion_cost)


def path_cost(graph: nx.DiGraph, path: list[str],
              traffic_edges: dict[tuple[str, str], dict[str, float]]) -> LegCost:
    total = LegCost(0.0, 0.0, 0.0)
    for u, v in zip(path[:-1], path[1:]):
        c = leg_cost(graph, u, v, traffic_edges)
        total.distance_m += c.distance_m
        total.travel_time_s += c.travel_time_s
        total.congestion_cost += c.congestion_cost
    return total
