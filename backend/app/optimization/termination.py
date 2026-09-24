"""
Termination conditions: max iterations, time budget, target cost, convergence
threshold. Stops on whichever condition is met first.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TerminationConfig:
    max_iterations: int = 500
    time_budget_s: float | None = None
    target_cost: float | None = None
    convergence_threshold: float | None = None  # min relative improvement over `patience` iters
    convergence_patience: int = 30


class TerminationTracker:
    def __init__(self, config: TerminationConfig):
        self.config = config
        self.start_time = time.monotonic()
        self.best_history: list[float] = []

    def should_stop(self, iteration_no: int, best_cost: float) -> tuple[bool, str]:
        self.best_history.append(best_cost)

        if iteration_no >= self.config.max_iterations:
            return True, "max_iterations"

        if self.config.time_budget_s is not None:
            if time.monotonic() - self.start_time >= self.config.time_budget_s:
                return True, "time_budget"

        if self.config.target_cost is not None and best_cost <= self.config.target_cost:
            return True, "target_cost"

        if self.config.convergence_threshold is not None and len(self.best_history) > self.config.convergence_patience:
            window = self.best_history[-self.config.convergence_patience:]
            improvement = (window[0] - window[-1]) / max(abs(window[0]), 1e-9)
            if improvement < self.config.convergence_threshold:
                return True, "convergence"

        return False, ""
