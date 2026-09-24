"""
Constraint repair for decoded routes: capacity, visit-once, depot, connectivity.
"""
from __future__ import annotations

from typing import Any

import networkx as nx

from app.optimization.decoder import DecodedRoute


def repair_capacity(routes: list[DecodedRoute], customers: list[dict[str, Any]], vehicles: list[dict[str, Any]]) -> list[DecodedRoute]:
    """If a vehicle's load exceeds capacity, move overflow customers to the
    next vehicle with spare capacity (creating one if none exists)."""
    for r in routes:
        capacity = vehicles[r.vehicle_index % len(vehicles)]["capacity_units"]
        if r.load_units <= capacity:
            continue
        overflow: list[int] = []
        load = 0
        kept: list[int] = []
        for cust_idx in r.stop_order:
            demand = customers[cust_idx]["demand_units"]
            if load + demand <= capacity:
                kept.append(cust_idx)
                load += demand
            else:
                overflow.append(cust_idx)
        r.stop_order = kept
        r.load_units = load
        if overflow:
            target_vehicle = (r.vehicle_index + 1) % len(vehicles)
            routes.append(DecodedRoute(vehicle_index=target_vehicle, stop_order=overflow,
                                        load_units=sum(customers[i]["demand_units"] for i in overflow)))
    return routes


def repair_visit_once(routes: list[DecodedRoute], num_customers: int) -> list[DecodedRoute]:
    """Remove duplicate visits; insert any required customer that was dropped
    into the least-loaded route."""
    seen: set[int] = set()
    for r in routes:
        deduped = []
        for c in r.stop_order:
            if c not in seen:
                deduped.append(c)
                seen.add(c)
        r.stop_order = deduped

    missing = [c for c in range(num_customers) if c not in seen]
    if missing and routes:
        routes.sort(key=lambda r: len(r.stop_order))
        for c in missing:
            routes[0].stop_order.append(c)
            seen.add(c)
    elif missing and not routes:
        routes.append(DecodedRoute(vehicle_index=0, stop_order=missing, load_units=0))
    return routes


def repair_connectivity(routes: list[DecodedRoute], graph: nx.DiGraph, customers: list[dict[str, Any]],
                         vehicles: list[dict[str, Any]], depot_node: str) -> tuple[list[DecodedRoute], bool]:
    """Drop customers whose graph node is unreachable from the route's own
    depot; report overall feasibility.

    Each route's vehicle may start from a different depot (the seeded
    fleet alternates between two) -- checking reachability from a single
    global `depot_node` for every route would wrongly mark a perfectly
    reachable route as infeasible whenever its vehicle's real depot
    differs from vehicles[0]'s. `depot_node` is kept only as the fallback
    for a vehicle dict that, for whatever reason, has no
    `start_depot_node` of its own.
    """
    feasible = True
    for r in routes:
        vehicle = vehicles[r.vehicle_index % len(vehicles)] if vehicles else {}
        route_depot = vehicle.get("start_depot_node") or depot_node
        reachable = []
        for c in r.stop_order:
            node = customers[c]["graph_node_id"]
            if node in graph and route_depot in graph and nx.has_path(graph, route_depot, node):
                reachable.append(c)
            else:
                feasible = False
        r.stop_order = reachable
    return routes, feasible


def repair_all(routes: list[DecodedRoute], customers: list[dict[str, Any]], vehicles: list[dict[str, Any]],
                graph: nx.DiGraph, depot_node: str) -> tuple[list[DecodedRoute], bool]:
    routes = repair_capacity(routes, customers, vehicles)
    routes = repair_visit_once(routes, len(customers))
    routes, feasible = repair_connectivity(routes, graph, customers, vehicles, depot_node)
    return routes, feasible
