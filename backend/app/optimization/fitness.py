"""
Configurable multi-objective fitness function, per the PRD:

J = w_distance * Distance + w_time * TravelTime + w_congestion * CongestionCost
    + w_late * LatePenalty + w_vehicle * VehicleCost + w_constraint * ConstraintPenalty
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from app.optimization.decoder import DecodedRoute
from app.optimization.route_cost import path_cost


@dataclass
class FitnessBreakdown:
    distance_m: float
    time_s: float
    congestion_cost: float
    late_penalty: float
    vehicle_cost: float
    constraint_penalty: float
    total: float


def _late_penalty(arrival_s: float, window_end_s: float | None) -> float:
    if window_end_s is None:
        return 0.0
    return max(arrival_s - window_end_s, 0.0)


def evaluate(
    routes: list[DecodedRoute],
    graph: nx.DiGraph,
    customers: list[dict[str, Any]],
    vehicles: list[dict[str, Any]],
    traffic_edges: dict[tuple[str, str], dict[str, float]],
    depot_node: str,
    end_depot_node: str,
    weights: dict[str, float],
    feasible: bool,
) -> FitnessBreakdown:
    total_distance = 0.0
    total_time = 0.0
    total_congestion = 0.0
    total_late = 0.0
    total_vehicle_cost = 0.0

    for r in routes:
        vehicle = vehicles[r.vehicle_index % len(vehicles)]
        # Each vehicle may depart/return to a different depot (the seeded
        # fleet alternates between two) -- fall back to the problem-wide
        # depot_node/end_depot_node only if this vehicle dict doesn't carry
        # its own (see optimization_service.build_problem_from_job).
        route_depot = vehicle.get("start_depot_node") or depot_node
        route_end_depot = vehicle.get("end_depot_node") or end_depot_node
        node_sequence = [route_depot] + [customers[c]["graph_node_id"] for c in r.stop_order] + [route_end_depot]

        try:
            full_path: list[str] = []
            for u, v in zip(node_sequence[:-1], node_sequence[1:]):
                segment = nx.shortest_path(graph, u, v, weight="length_m")
                full_path.extend(segment[:-1])
            full_path.append(node_sequence[-1])
        except nx.NetworkXNoPath:
            total_late += 1e6  # heavy penalty; connectivity repair should have caught this
            continue

        cost = path_cost(graph, full_path, traffic_edges)
        total_distance += cost.distance_m
        total_time += cost.travel_time_s
        total_congestion += cost.congestion_cost

        elapsed = 0.0
        for c in r.stop_order:
            cust = customers[c]
            elapsed += cust.get("service_seconds", 0)
            window_end = cust.get("window_end_seconds")
            total_late += _late_penalty(elapsed, window_end)

        total_vehicle_cost += vehicle.get("fixed_cost", 0.0) + vehicle.get("cost_per_km", 0.0) * (cost.distance_m / 1000.0)

    constraint_penalty = 0.0 if feasible else 1e5

    total = (
        weights.get("distance", 0.0) * total_distance
        + weights.get("time", 0.0) * total_time
        + weights.get("congestion", 0.0) * total_congestion
        + weights.get("late", 0.0) * total_late
        + weights.get("vehicle", 0.0) * total_vehicle_cost
        + weights.get("constraint", 1.0) * constraint_penalty
    )

    return FitnessBreakdown(
        distance_m=total_distance,
        time_s=total_time,
        congestion_cost=total_congestion,
        late_penalty=total_late,
        vehicle_cost=total_vehicle_cost,
        constraint_penalty=constraint_penalty,
        total=total,
    )
