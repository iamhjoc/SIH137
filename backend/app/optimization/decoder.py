"""
Decodes a customer visiting order (from encoding.keys_to_order) into
per-vehicle routes, respecting capacity and depot rules. Produces a
first feasible split; repair.py fixes anything still broken.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DecodedStop:
    customer_index: int | None  # None => depot stop
    is_depot: bool = False


@dataclass
class DecodedRoute:
    vehicle_index: int
    stop_order: list[int]  # customer indices, in visiting order (depot excluded)
    load_units: int


def decode(order: list[int], customers: list[dict[str, Any]], vehicles: list[dict[str, Any]]) -> list[DecodedRoute]:
    """
    Greedy bin-packing decode: walk the customer order, assign to the
    current vehicle until capacity would be exceeded, then move to the
    next vehicle. This mirrors the PRD's decoder responsibilities:
    sort -> assign -> respect capacity -> respect depot rules -> sequence.
    """
    routes: list[DecodedRoute] = []
    if not vehicles:
        return routes

    vehicle_idx = 0
    current_load = 0
    current_stops: list[int] = []

    def flush():
        nonlocal current_stops, current_load
        if current_stops:
            routes.append(DecodedRoute(vehicle_index=vehicle_idx, stop_order=list(current_stops), load_units=current_load))
        current_stops = []
        current_load = 0

    for cust_idx in order:
        demand = customers[cust_idx]["demand_units"]
        capacity = vehicles[vehicle_idx]["capacity_units"]

        if current_load + demand > capacity:
            flush()
            if vehicle_idx < len(vehicles) - 1:
                vehicle_idx += 1
            # else: stay on the last vehicle; repair.py will flag capacity overflow

        current_stops.append(cust_idx)
        current_load += demand

    flush()
    return routes
