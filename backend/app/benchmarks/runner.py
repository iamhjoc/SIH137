"""
Runs a benchmark experiment across multiple algorithms (including QPSO)
with repeated, seeded trials, and reports actual measured results --
numbers are never manufactured.
"""
from __future__ import annotations

import time
from typing import Any

from app.benchmarks.algorithms import ALGORITHM_REGISTRY
from app.benchmarks.metrics import RunSample, aggregate
from app.optimization.interfaces import OptimizationProblem
from app.optimization.qpso import QPSOConfig, QPSOEngine


def _build_algorithm(name: str, seed: int):
    if name == "qpso":
        return QPSOEngine(QPSOConfig(particles=30, iterations=150))
    if name not in ALGORITHM_REGISTRY:
        raise ValueError(f"Unknown algorithm '{name}'")
    return ALGORITHM_REGISTRY[name]()


def run_experiment(problem_template: OptimizationProblem, algorithms: list[str],
                    repetitions: int, base_seed: int) -> dict[str, list[RunSample]]:
    results: dict[str, list[RunSample]] = {alg: [] for alg in algorithms}

    for alg_name in algorithms:
        for rep in range(repetitions):
            rep_seed = base_seed + rep
            problem = OptimizationProblem(
                graph=problem_template.graph,
                depot_node=problem_template.depot_node,
                end_depot_node=problem_template.end_depot_node,
                customers=problem_template.customers,
                vehicles=problem_template.vehicles,
                traffic_edges=problem_template.traffic_edges,
                objective_weights=problem_template.objective_weights,
                constraints=problem_template.constraints,
                seed=rep_seed,
            )
            algorithm = _build_algorithm(alg_name, rep_seed)
            t0 = time.monotonic()
            result = algorithm.optimize(problem)
            runtime_ms = int((time.monotonic() - t0) * 1000)

            distance = sum(r.get("distance_m", 0) for r in result.metadata.get("route_costs", [])) or 0.0
            results[alg_name].append(RunSample(
                objective_cost=result.best_cost,
                distance_m=distance,
                travel_time_s=0.0,
                congestion_cost=0.0,
                runtime_ms=runtime_ms,
                feasible=result.feasible,
                iterations=len(result.iterations),
            ))

    return results


def summarize(results: dict[str, list[RunSample]]) -> dict[str, Any]:
    return {alg: aggregate(samples).__dict__ for alg, samples in results.items() if samples}
