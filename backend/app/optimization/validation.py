"""
Pre-optimization feasibility checks (section 48). If infeasible, the
expensive optimization job must NOT be queued.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx

MAX_MAPPING_DISTANCE_M = 500.0


@dataclass
class FeasibilityResult:
    feasible: bool
    errors: list[str] = field(default_factory=list)


def check_feasibility(
    customers: list[dict[str, Any]],
    vehicles: list[dict[str, Any]],
    graph: nx.DiGraph,
    depot_node: str,
    objective_weights: dict[str, float],
    traffic_scenario_valid: bool,
) -> FeasibilityResult:
    errors: list[str] = []

    if len(customers) == 0:
        errors.append("At least one customer is required.")
    if len(vehicles) == 0:
        errors.append("At least one vehicle is required.")

    total_demand = sum(c.get("demand_units", 0) for c in customers)
    total_capacity = sum(v.get("capacity_units", 0) for v in vehicles)
    if total_demand > total_capacity:
        errors.append(f"Total demand ({total_demand}) exceeds total fleet capacity ({total_capacity}).")

    for c in customers:
        node = c.get("graph_node_id")
        if node is None or node not in graph:
            errors.append(f"Customer {c.get('id')} could not be mapped to the road graph (CUSTOMER_GRAPH_MAPPING_FAILED).")
            continue
        if depot_node in graph and not nx.has_path(graph, depot_node, node):
            errors.append(f"Customer {c.get('id')} is not reachable from the depot.")

    for v in vehicles:
        if not v.get("start_depot_id") or not v.get("end_depot_id"):
            errors.append(f"Vehicle {v.get('id')} is missing a valid start/end depot.")

    if depot_node not in graph:
        errors.append("Depot does not map to a valid graph node.")

    total_weight = sum(objective_weights.values()) if objective_weights else 0.0
    if total_weight <= 0:
        errors.append("Objective weights must sum to a positive value.")

    if not traffic_scenario_valid:
        errors.append("Referenced traffic scenario is invalid or does not belong to this project.")

    return FeasibilityResult(feasible=len(errors) == 0, errors=errors)
