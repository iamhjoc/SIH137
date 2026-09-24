"""
Common interfaces so QPSO and baseline algorithms (GA/ACO/PSO/Dijkstra/A*)
are interchangeable within the benchmark runner.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class OptimizationProblem:
    """Everything an algorithm needs to produce a solution, decoupled from the DB."""
    graph: nx.DiGraph
    depot_node: str
    end_depot_node: str
    customers: list[dict[str, Any]]          # [{id, graph_node_id, demand_units, ...}]
    vehicles: list[dict[str, Any]]           # [{id, capacity_units, cost_per_km, ...}]
    traffic_edges: dict[tuple[str, str], dict[str, float]]  # (u,v) -> {speed_kmh, congestion_factor}
    objective_weights: dict[str, float]
    constraints: dict[str, bool]
    seed: int


@dataclass
class IterationRecord:
    iteration_no: int
    best_cost: float
    mean_cost: float
    diversity: float
    elapsed_ms: int


@dataclass
class OptimizationResult:
    best_cost: float
    routes: list[dict[str, Any]]             # decoded per-vehicle route with stops/legs
    iterations: list[IterationRecord] = field(default_factory=list)
    feasible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class RoutingAlgorithm(ABC):
    """Common interface implemented by QPSO and every baseline algorithm."""

    name: str = "base"

    @abstractmethod
    def optimize(self, problem: OptimizationProblem, progress_callback=None) -> OptimizationResult:
        ...
