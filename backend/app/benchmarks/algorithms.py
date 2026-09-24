"""
Baseline routing algorithms, all implementing RoutingAlgorithm so the
benchmark runner can treat QPSO and classical algorithms interchangeably.
None of these are faked -- each actually computes a solution and its real
cost via the shared fitness function.
"""
from __future__ import annotations

import time

import networkx as nx
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


def _evaluate_order(order: list[int], problem: OptimizationProblem):
    routes = decode(order, problem.customers, problem.vehicles)
    routes, feasible = repair_all(routes, problem.customers, problem.vehicles, problem.graph, problem.depot_node)
    fitness = evaluate(
        routes, problem.graph, problem.customers, problem.vehicles, problem.traffic_edges,
        problem.depot_node, problem.end_depot_node, problem.objective_weights, feasible,
    )
    return fitness.total, routes, feasible


class DijkstraNearestNeighborAlgorithm(RoutingAlgorithm):
    """Greedy nearest-neighbor construction using Dijkstra shortest paths."""
    name = "dijkstra"

    def optimize(self, problem: OptimizationProblem, progress_callback=None) -> OptimizationResult:
        remaining = list(range(len(problem.customers)))
        order: list[int] = []
        current_node = problem.depot_node

        while remaining:
            best_idx, best_dist = None, float("inf")
            for idx in remaining:
                node = problem.customers[idx]["graph_node_id"]
                try:
                    dist = nx.shortest_path_length(problem.graph, current_node, node, weight="length_m")
                except nx.NetworkXNoPath:
                    dist = float("inf")
                if dist < best_dist:
                    best_idx, best_dist = idx, dist
            order.append(best_idx)
            remaining.remove(best_idx)
            current_node = problem.customers[best_idx]["graph_node_id"]

        cost, routes, feasible = _evaluate_order(order, problem)
        return OptimizationResult(best_cost=cost, routes=[r.__dict__ for r in routes], feasible=feasible)


class AStarNearestNeighborAlgorithm(RoutingAlgorithm):
    """Same greedy construction, but path cost via A* with a Euclidean heuristic."""
    name = "astar"

    def optimize(self, problem: OptimizationProblem, progress_callback=None) -> OptimizationResult:
        def heuristic(u, v):
            du, dv = problem.graph.nodes[u], problem.graph.nodes[v]
            return ((du["lat"] - dv["lat"]) ** 2 + (du["lon"] - dv["lon"]) ** 2) ** 0.5 * 100_000

        remaining = list(range(len(problem.customers)))
        order: list[int] = []
        current_node = problem.depot_node

        while remaining:
            best_idx, best_dist = None, float("inf")
            for idx in remaining:
                node = problem.customers[idx]["graph_node_id"]
                try:
                    dist = nx.astar_path_length(problem.graph, current_node, node, heuristic=heuristic, weight="length_m")
                except nx.NetworkXNoPath:
                    dist = float("inf")
                if dist < best_dist:
                    best_idx, best_dist = idx, dist
            order.append(best_idx)
            remaining.remove(best_idx)
            current_node = problem.customers[best_idx]["graph_node_id"]

        cost, routes, feasible = _evaluate_order(order, problem)
        return OptimizationResult(best_cost=cost, routes=[r.__dict__ for r in routes], feasible=feasible)


class ClassicalPSOAlgorithm(RoutingAlgorithm):
    """Classical (non-quantum) PSO variant with inertia weight + cognitive/social terms."""
    name = "pso"

    def __init__(self, particles: int = 30, iterations: int = 200, w: float = 0.7, c1: float = 1.5, c2: float = 1.5):
        self.particles, self.iterations, self.w, self.c1, self.c2 = particles, iterations, w, c1, c2

    def optimize(self, problem: OptimizationProblem, progress_callback=None) -> OptimizationResult:
        n = len(problem.customers)
        rng = np.random.default_rng(problem.seed)
        if n == 0:
            return OptimizationResult(best_cost=0.0, routes=[], feasible=False)

        pos = initial_population(self.particles, n, rng)
        vel = rng.uniform(-0.1, 0.1, size=pos.shape)
        pbest_pos, pbest_cost = pos.copy(), np.full(self.particles, np.inf)
        gbest_pos, gbest_cost, gbest_routes = pos[0].copy(), np.inf, []

        iters: list[IterationRecord] = []
        t0 = time.monotonic()
        for it in range(1, self.iterations + 1):
            for i in range(self.particles):
                cost, routes, feasible = _evaluate_order(keys_to_order(pos[i]), problem)
                if cost < pbest_cost[i]:
                    pbest_cost[i], pbest_pos[i] = cost, pos[i].copy()
                if cost < gbest_cost:
                    gbest_cost, gbest_pos, gbest_routes = cost, pos[i].copy(), routes

            r1, r2 = rng.random(pos.shape), rng.random(pos.shape)
            vel = self.w * vel + self.c1 * r1 * (pbest_pos - pos) + self.c2 * r2 * (gbest_pos - pos)
            pos = np.clip(pos + vel, 0.0, 1.0)

            iters.append(IterationRecord(it, float(gbest_cost), float(pbest_cost.mean()),
                                          float(np.std(pos)), int((time.monotonic() - t0) * 1000)))

        return OptimizationResult(best_cost=float(gbest_cost),
                                   routes=[r.__dict__ for r in gbest_routes], iterations=iters, feasible=True)


class GeneticAlgorithm(RoutingAlgorithm):
    """Standard GA over the random-key encoding: tournament select, crossover, mutate."""
    name = "ga"

    def __init__(self, population_size: int = 40, generations: int = 200, mutation_rate: float = 0.1):
        self.population_size, self.generations, self.mutation_rate = population_size, generations, mutation_rate

    def optimize(self, problem: OptimizationProblem, progress_callback=None) -> OptimizationResult:
        n = len(problem.customers)
        rng = np.random.default_rng(problem.seed)
        if n == 0:
            return OptimizationResult(best_cost=0.0, routes=[], feasible=False)

        pop = initial_population(self.population_size, n, rng)
        best_cost, best_routes = np.inf, []
        iters: list[IterationRecord] = []
        t0 = time.monotonic()

        for gen in range(1, self.generations + 1):
            costs = np.zeros(self.population_size)
            all_routes = []
            for i in range(self.population_size):
                cost, routes, feasible = _evaluate_order(keys_to_order(pop[i]), problem)
                costs[i] = cost
                all_routes.append(routes)
                if cost < best_cost:
                    best_cost, best_routes = cost, routes

            # Tournament selection + single-point crossover + mutation
            new_pop = np.zeros_like(pop)
            for i in range(self.population_size):
                a, b = rng.integers(0, self.population_size, size=2)
                parent1 = pop[a] if costs[a] < costs[b] else pop[b]
                c, d = rng.integers(0, self.population_size, size=2)
                parent2 = pop[c] if costs[c] < costs[d] else pop[d]

                point = rng.integers(1, max(n, 2))
                child = np.concatenate([parent1[:point], parent2[point:]])

                mutate_mask = rng.random(n) < self.mutation_rate
                child[mutate_mask] = rng.random(mutate_mask.sum())
                new_pop[i] = child

            pop = new_pop
            iters.append(IterationRecord(gen, float(best_cost), float(costs.mean()),
                                          float(np.std(pop)), int((time.monotonic() - t0) * 1000)))

        return OptimizationResult(best_cost=float(best_cost),
                                   routes=[r.__dict__ for r in best_routes], iterations=iters, feasible=True)


class AntColonyOptimization(RoutingAlgorithm):
    """ACO over the customer-visit-order construction graph with pheromone trails."""
    name = "aco"

    def __init__(self, ants: int = 25, iterations: int = 150, evaporation: float = 0.3, alpha: float = 1.0, beta: float = 2.0):
        self.ants, self.iterations, self.evaporation, self.alpha, self.beta = ants, iterations, evaporation, alpha, beta

    def optimize(self, problem: OptimizationProblem, progress_callback=None) -> OptimizationResult:
        n = len(problem.customers)
        rng = np.random.default_rng(problem.seed)
        if n == 0:
            return OptimizationResult(best_cost=0.0, routes=[], feasible=False)

        pheromone = np.ones((n, n))
        best_cost, best_routes = np.inf, []
        iters: list[IterationRecord] = []
        t0 = time.monotonic()

        # Heuristic desirability = inverse straight-line distance between customers.
        lat = np.array([problem.graph.nodes[c["graph_node_id"]]["lat"] for c in problem.customers])
        lon = np.array([problem.graph.nodes[c["graph_node_id"]]["lon"] for c in problem.customers])
        dist_matrix = np.sqrt((lat[:, None] - lat[None, :]) ** 2 + (lon[:, None] - lon[None, :]) ** 2) + 1e-6
        eta = 1.0 / dist_matrix

        for it in range(1, self.iterations + 1):
            iteration_costs = []
            iteration_orders = []
            for _ in range(self.ants):
                unvisited = list(range(n))
                current = rng.integers(0, n)
                order = [current]
                unvisited.remove(current)
                while unvisited:
                    weights = np.array([
                        (pheromone[current, j] ** self.alpha) * (eta[current, j] ** self.beta)
                        for j in unvisited
                    ])
                    weights = weights / weights.sum() if weights.sum() > 0 else np.ones(len(unvisited)) / len(unvisited)
                    nxt = rng.choice(unvisited, p=weights)
                    order.append(nxt)
                    unvisited.remove(nxt)
                    current = nxt

                cost, routes, feasible = _evaluate_order(order, problem)
                iteration_costs.append(cost)
                iteration_orders.append(order)
                if cost < best_cost:
                    best_cost, best_routes = cost, routes

            pheromone *= (1 - self.evaporation)
            for order, cost in zip(iteration_orders, iteration_costs):
                deposit = 1.0 / max(cost, 1e-6)
                for a, b in zip(order[:-1], order[1:]):
                    pheromone[a, b] += deposit

            iters.append(IterationRecord(it, float(best_cost), float(np.mean(iteration_costs)),
                                          float(np.std(pheromone)), int((time.monotonic() - t0) * 1000)))

        return OptimizationResult(best_cost=float(best_cost),
                                   routes=[r.__dict__ for r in best_routes], iterations=iters, feasible=True)


ALGORITHM_REGISTRY: dict[str, type[RoutingAlgorithm]] = {
    "dijkstra": DijkstraNearestNeighborAlgorithm,
    "astar": AStarNearestNeighborAlgorithm,
    "pso": ClassicalPSOAlgorithm,
    "ga": GeneticAlgorithm,
    "aco": AntColonyOptimization,
}
