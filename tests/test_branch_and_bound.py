"""Branch & Bound bound validity, budgets, and instrumentation."""

import random

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.eval.feasibility import check
from core.exact.branch_and_bound import (
    BranchAndBoundSolver,
    completion_lower_bound,
)
from core.exact.brute_force import BruteForceSolver
from core.model.instance import Instance
from core.model.vehicle import Vehicle
from core.reporting.status import SolveStatus, StopReason
from core.solver import Budget


@pytest.mark.parametrize("generator", [random_euclidean_tsp, random_asymmetric_tsp])
@pytest.mark.parametrize("n", range(1, 8))
@pytest.mark.parametrize("seed", range(8))
def test_root_bound_never_exceeds_brute_force_optimum(generator, n, seed):
    instance = generator(n, seed)
    optimum = BruteForceSolver().solve(instance)[1].objective_value
    assert completion_lower_bound(instance) <= optimum


@pytest.mark.parametrize("generator", [random_euclidean_tsp, random_asymmetric_tsp])
@pytest.mark.parametrize("seed", range(6))
def test_partial_bound_never_exceeds_a_known_completion(generator, seed):
    instance = generator(8, seed)
    customers = list(instance.customer_indices)
    random.Random(seed).shuffle(customers)
    prefix = tuple(customers[:3])

    # Any concrete extension is an upper bound on the best extension of this
    # prefix, so the relaxation must not exceed it.
    candidate = prefix + tuple(customers[3:])
    depot = instance.depot_index
    previous = depot
    candidate_cost = 0
    for node in candidate:
        candidate_cost += instance.matrix.cost(previous, node)
        previous = node
    candidate_cost += instance.matrix.cost(previous, depot)

    assert completion_lower_bound(instance, prefix) <= candidate_cost


def test_node_cap_preserves_frontier_lower_bound_and_incumbent():
    # This directed instance gives nearest neighbour a cost of 103 while a
    # cheaper tour remains in the frontier after the root expansion.
    from core.distance.matrix import DistanceMatrix
    from core.model.stop import Stop
    from core.model.units import Unit

    matrix = DistanceMatrix(
        [
            0, 1, 2, 2,
            100, 0, 1, 5,
            1, 1, 0, 100,
            1, 1, 1, 0,
        ],
        4,
        Unit.TSPLIB,
    )
    instance = Instance.single_vehicle_tsp(
        "greedy trap", tuple(Stop(id=i) for i in range(4)), matrix
    )
    optimum = BruteForceSolver().solve(instance)[1].objective_value
    solution, report = BranchAndBoundSolver().solve(
        instance, Budget(max_nodes=1)
    )

    assert check(instance, solution).is_feasible
    assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
    assert report.stop_reason is StopReason.NODE_CAP
    assert report.nodes_explored == 1
    assert 0 <= report.best_lower_bound <= optimum <= report.objective_value
    assert not report.status.permits_word_optimal


def test_memory_cap_is_honoured_before_root_allocation(monkeypatch):
    import core.exact.branch_and_bound as module

    monkeypatch.setattr(module, "_BASE_STATE_BYTES", 2 * 1024 * 1024)
    instance = random_asymmetric_tsp(7, seed=2)
    solution, report = BranchAndBoundSolver().solve(
        instance, Budget(max_memory_mb=1)
    )
    assert check(instance, solution).is_feasible
    assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
    assert report.stop_reason is StopReason.MEMORY_CAP
    assert report.nodes_created == 0
    assert 0 < report.peak_memory_mb <= 1


def test_wall_clock_cap_returns_incumbent_without_claiming_proof(monkeypatch):
    import core.exact.branch_and_bound as module

    ticks = iter(i / 1000 for i in range(100))
    monkeypatch.setattr(module.time, "perf_counter", lambda: next(ticks))
    instance = random_asymmetric_tsp(8, seed=11)
    solution, report = BranchAndBoundSolver().solve(
        instance, Budget(wall_time_ms=1)
    )

    assert check(instance, solution).is_feasible
    assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
    assert report.stop_reason is StopReason.TIMEOUT
    assert report.best_lower_bound == 0
    assert report.nodes_explored == 0


def test_completed_report_contains_search_and_bound_instrumentation():
    instance = random_asymmetric_tsp(8, seed=19)
    solution, report = BranchAndBoundSolver().solve(instance)

    assert check(instance, solution).is_feasible
    assert report.status is SolveStatus.PROVEN_OPTIMAL_TSP
    assert report.stop_reason is StopReason.OPTIMAL
    assert report.best_lower_bound == report.objective_value
    assert report.nodes_created > 0
    assert report.nodes_explored >= 0
    assert report.nodes_pruned > 0
    assert report.peak_frontier > 0
    assert report.bound_time_ms >= 0
    assert report.extra["bound"] == "min_in_out"
    assert report.extra["search_strategy"] == "best_first"


def test_large_unbudgeted_run_is_refused_but_budgeted_exploration_is_allowed():
    instance = random_euclidean_tsp(16, seed=5)  # 15 customers > guard
    solver = BranchAndBoundSolver()
    with pytest.raises(ValueError, match="unbudgeted"):
        solver.solve(instance)

    solution, report = solver.solve(instance, Budget(max_nodes=1))
    assert check(instance, solution).is_feasible
    assert report.nodes_explored <= 1
    assert report.status in {
        SolveStatus.PROVEN_OPTIMAL_TSP,
        SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
    }


def test_partial_bound_rejects_invalid_paths():
    instance = random_euclidean_tsp(5, seed=0)
    with pytest.raises(ValueError, match="duplicate"):
        completion_lower_bound(instance, (1, 1))
    with pytest.raises(ValueError, match="customer indices"):
        completion_lower_bound(instance, (instance.depot_index,))


def test_refuses_non_tsp_instances():
    tsp = random_euclidean_tsp(5, seed=2)
    cvrp = Instance(
        name="fleet",
        stops=tsp.stops,
        vehicles=(Vehicle(0), Vehicle(1)),
        matrix=tsp.matrix,
    )
    with pytest.raises(ValueError, match="TSP only"):
        BranchAndBoundSolver().solve(cvrp)
