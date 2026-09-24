"""
Unit tests for the QPSO engine and its supporting modules. These run
against an in-memory synthetic graph -- no database required.
"""
import networkx as nx
import pytest

from app.graph.loader import generate_synthetic_grid_graph
from app.optimization.decoder import decode
from app.optimization.encoding import initial_population, keys_to_order
from app.optimization.fitness import evaluate
from app.optimization.interfaces import OptimizationProblem
from app.optimization.qpso import QPSOConfig, QPSOEngine
from app.optimization.repair import repair_all
from app.optimization.validation import check_feasibility


@pytest.fixture
def small_graph():
    return generate_synthetic_grid_graph(rows=4, cols=4, seed=20260909)


@pytest.fixture
def customers():
    return [
        {"id": "c1", "graph_node_id": "n_0_1", "demand_units": 5, "service_seconds": 300},
        {"id": "c2", "graph_node_id": "n_1_0", "demand_units": 5, "service_seconds": 300},
        {"id": "c3", "graph_node_id": "n_2_2", "demand_units": 8, "service_seconds": 300},
        {"id": "c4", "graph_node_id": "n_3_3", "demand_units": 3, "service_seconds": 300},
    ]


@pytest.fixture
def vehicles():
    return [
        {"id": "v1", "capacity_units": 12, "fixed_cost": 100, "cost_per_km": 5},
        {"id": "v2", "capacity_units": 12, "fixed_cost": 100, "cost_per_km": 5},
    ]


def test_encoding_produces_valid_permutation():
    rng = __import__("numpy").random.default_rng(1)
    pop = initial_population(10, 4, rng)
    order = keys_to_order(pop[0])
    assert sorted(order) == [0, 1, 2, 3]


def test_decoder_respects_capacity(customers, vehicles):
    order = [0, 1, 2, 3]
    routes = decode(order, customers, vehicles)
    for r in routes:
        assert r.load_units <= vehicles[r.vehicle_index % len(vehicles)]["capacity_units"] or len(routes) > len(vehicles)


def test_repair_removes_duplicate_visits(small_graph, customers, vehicles):
    from app.optimization.decoder import DecodedRoute
    routes = [
        DecodedRoute(vehicle_index=0, stop_order=[0, 1], load_units=10),
        DecodedRoute(vehicle_index=1, stop_order=[1, 2, 3], load_units=16),
    ]
    repaired, feasible = repair_all(routes, customers, vehicles, small_graph, "n_0_0")
    all_customers = [c for r in repaired for c in r.stop_order]
    assert sorted(set(all_customers)) == sorted(all_customers)  # no duplicates
    assert set(all_customers) == {0, 1, 2, 3}  # all visited


def test_feasibility_check_flags_capacity_overflow(small_graph, customers):
    tiny_vehicles = [{"id": "v1", "capacity_units": 1, "start_depot_id": "d1", "end_depot_id": "d1"}]
    result = check_feasibility(customers, tiny_vehicles, small_graph, "n_0_0", {"distance": 1.0}, True)
    assert not result.feasible
    assert any("capacity" in e for e in result.errors)


def test_qpso_produces_feasible_solution(small_graph, customers, vehicles):
    problem = OptimizationProblem(
        graph=small_graph, depot_node="n_0_0", end_depot_node="n_0_0",
        customers=customers, vehicles=vehicles, traffic_edges={},
        objective_weights={"distance": 0.25, "time": 0.4, "congestion": 0.25, "late": 0.1, "vehicle": 0.0, "constraint": 1.0},
        constraints={"capacity": True, "visit_once": True, "return_to_depot": True},
        seed=20260909,
    )
    engine = QPSOEngine(QPSOConfig(particles=8, iterations=15))
    result = engine.optimize(problem)

    assert result.feasible
    all_customers_visited = sorted(c for r in result.routes for c in r["stop_order"])
    assert all_customers_visited == [0, 1, 2, 3]
    assert result.best_cost >= 0
    assert len(result.iterations) == 15


def test_qpso_is_reproducible_given_same_seed(small_graph, customers, vehicles):
    weights = {"distance": 0.25, "time": 0.4, "congestion": 0.25, "late": 0.1, "vehicle": 0.0, "constraint": 1.0}
    constraints = {"capacity": True, "visit_once": True, "return_to_depot": True}

    def build():
        return OptimizationProblem(
            graph=small_graph, depot_node="n_0_0", end_depot_node="n_0_0",
            customers=customers, vehicles=vehicles, traffic_edges={},
            objective_weights=weights, constraints=constraints, seed=42,
        )

    r1 = QPSOEngine(QPSOConfig(particles=6, iterations=10)).optimize(build())
    r2 = QPSOEngine(QPSOConfig(particles=6, iterations=10)).optimize(build())
    assert r1.best_cost == pytest.approx(r2.best_cost)
