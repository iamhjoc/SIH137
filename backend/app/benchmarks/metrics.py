"""
Aggregate benchmark metrics across repeated runs: mean/std/best/worst cost,
runtime, distance, travel time, congestion, feasibility rate.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass
class RunSample:
    objective_cost: float
    distance_m: float
    travel_time_s: float
    congestion_cost: float
    runtime_ms: int
    feasible: bool
    iterations: int


@dataclass
class AggregateMetrics:
    mean_cost: float
    std_cost: float
    best_cost: float
    worst_cost: float
    mean_runtime_ms: float
    mean_distance_m: float
    mean_travel_time_s: float
    mean_congestion_cost: float
    feasibility_rate: float
    mean_iterations: float


def aggregate(samples: list[RunSample]) -> AggregateMetrics:
    costs = [s.objective_cost for s in samples]
    return AggregateMetrics(
        mean_cost=statistics.mean(costs),
        std_cost=statistics.pstdev(costs) if len(costs) > 1 else 0.0,
        best_cost=min(costs),
        worst_cost=max(costs),
        mean_runtime_ms=statistics.mean(s.runtime_ms for s in samples),
        mean_distance_m=statistics.mean(s.distance_m for s in samples),
        mean_travel_time_s=statistics.mean(s.travel_time_s for s in samples),
        mean_congestion_cost=statistics.mean(s.congestion_cost for s in samples),
        feasibility_rate=sum(1 for s in samples if s.feasible) / len(samples),
        mean_iterations=statistics.mean(s.iterations for s in samples),
    )
