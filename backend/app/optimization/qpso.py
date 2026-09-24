"""
Quantum-behaved Particle Swarm Optimization (QPSO) engine over the
random-key encoding for multi-vehicle routing.

Each particle position is a real-valued vector (one gene per customer).
Standard QPSO update (Sun et al.):
  mbest = mean of all personal-best positions
  For each particle i, dimension d:
    phi ~ U(0,1)
    p = phi * pbest[i,d] + (1-phi) * gbest[d]
    u ~ U(0,1)
    x[i,d] = p +/- beta * |mbest[d] - x[i,d]| * ln(1/u)
  sign chosen with probability 0.5 each.

`beta` linearly interpolates from beta_start -> beta_end across iterations,
giving broad exploration early and tighter exploitation late.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.optimization.decoder import decode
from app.optimization.encoding import initial_population, keys_to_order
from app.optimization.fitness import evaluate
from app.optimization.interfaces import (
    IterationRecord,
    OptimizationProblem,
    OptimizationResult,
    RoutingAlgorithm,
)
from app.optimization.repair import repair_all
from app.optimization.termination import TerminationConfig, TerminationTracker

ProgressCallback = Callable[[IterationRecord], None]


@dataclass
class QPSOConfig:
    particles: int = 40
    iterations: int = 500
    beta_start: float = 1.0
    beta_end: float = 0.5
    time_budget_s: float | None = None
    target_cost: float | None = None
    convergence_threshold: float | None = None


def _evaluate_particle(
    keys: np.ndarray,
    problem: OptimizationProblem,
) -> tuple[float, list, bool]:
    order = keys_to_order(keys)
    routes = decode(order, problem.customers, problem.vehicles)
    routes, feasible = repair_all(routes, problem.customers, problem.vehicles, problem.graph, problem.depot_node)
    fitness = evaluate(
        routes, problem.graph, problem.customers, problem.vehicles, problem.traffic_edges,
        problem.depot_node, problem.end_depot_node, problem.objective_weights, feasible,
    )
    return fitness.total, routes, feasible


class QPSOEngine(RoutingAlgorithm):
    name = "qpso"

    def __init__(self, config: QPSOConfig | None = None):
        self.config = config or QPSOConfig()

    def optimize(self, problem: OptimizationProblem, progress_callback: ProgressCallback | None = None) -> OptimizationResult:
        cfg = self.config
        num_customers = len(problem.customers)
        rng = np.random.default_rng(problem.seed)

        if num_customers == 0:
            return OptimizationResult(best_cost=0.0, routes=[], feasible=False,
                                       metadata={"reason": "no_customers"})

        positions = initial_population(cfg.particles, num_customers, rng)
        pbest_positions = positions.copy()
        pbest_costs = np.full(cfg.particles, np.inf)

        gbest_position = positions[0].copy()
        gbest_cost = np.inf
        gbest_routes: list = []
        gbest_feasible = False

        term_tracker = TerminationTracker(TerminationConfig(
            max_iterations=cfg.iterations,
            time_budget_s=cfg.time_budget_s,
            target_cost=cfg.target_cost,
            convergence_threshold=cfg.convergence_threshold,
        ))

        iteration_records: list[IterationRecord] = []
        start = time.monotonic()

        # Evaluate initial swarm
        costs = np.zeros(cfg.particles)
        for i in range(cfg.particles):
            cost, routes, feasible = _evaluate_particle(positions[i], problem)
            costs[i] = cost
            if cost < pbest_costs[i]:
                pbest_costs[i] = cost
                pbest_positions[i] = positions[i].copy()
            if cost < gbest_cost:
                gbest_cost = cost
                gbest_position = positions[i].copy()
                gbest_routes = routes
                gbest_feasible = feasible

        iteration_no = 0
        while True:
            iteration_no += 1
            beta = cfg.beta_start + (cfg.beta_end - cfg.beta_start) * (iteration_no / max(cfg.iterations, 1))
            mbest = pbest_positions.mean(axis=0)

            for i in range(cfg.particles):
                phi = rng.random(num_customers)
                p = phi * pbest_positions[i] + (1 - phi) * gbest_position
                u = rng.random(num_customers)
                u = np.clip(u, 1e-9, 1 - 1e-9)
                sign = rng.choice([-1.0, 1.0], size=num_customers)
                positions[i] = p + sign * beta * np.abs(mbest - positions[i]) * np.log(1.0 / u)
                positions[i] = np.clip(positions[i], 0.0, 1.0)

                cost, routes, feasible = _evaluate_particle(positions[i], problem)
                costs[i] = cost
                if cost < pbest_costs[i]:
                    pbest_costs[i] = cost
                    pbest_positions[i] = positions[i].copy()
                if cost < gbest_cost:
                    gbest_cost = cost
                    gbest_position = positions[i].copy()
                    gbest_routes = routes
                    gbest_feasible = feasible

            elapsed_ms = int((time.monotonic() - start) * 1000)
            record = IterationRecord(
                iteration_no=iteration_no,
                best_cost=float(gbest_cost),
                mean_cost=float(costs.mean()),
                diversity=float(np.std(positions)),
                elapsed_ms=elapsed_ms,
            )
            iteration_records.append(record)
            if progress_callback:
                progress_callback(record)

            stop, reason = term_tracker.should_stop(iteration_no, gbest_cost)
            if stop:
                break

        decoded_routes = [
            {
                "vehicle_index": r.vehicle_index,
                "stop_order": r.stop_order,
                "load_units": r.load_units,
            }
            for r in gbest_routes
        ]

        return OptimizationResult(
            best_cost=float(gbest_cost),
            routes=decoded_routes,
            iterations=iteration_records,
            feasible=gbest_feasible,
            metadata={"termination_reason": reason, "final_iteration": iteration_no},
        )
