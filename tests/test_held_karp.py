"""Held--Karp resource handling and reporting tests."""

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.eval.feasibility import check
from core.exact.held_karp import (
    ESTIMATED_BYTES_PER_STATE,
    HeldKarpSolver,
    projected_state_count,
)
from core.model.instance import Instance
from core.model.vehicle import Vehicle
from core.reporting.status import SolveStatus, StopReason
from core.solver import Budget


@pytest.mark.parametrize(
    ("customers", "states"),
    [(0, 0), (1, 1), (2, 4), (3, 12), (4, 32), (10, 5120)],
)
def test_projected_state_count_matches_the_dp_recurrence(customers, states):
    assert projected_state_count(customers) == states


def test_projected_state_count_rejects_negative_input():
    with pytest.raises(ValueError, match="non-negative"):
        projected_state_count(-1)


@pytest.mark.parametrize("generator", [random_euclidean_tsp, random_asymmetric_tsp])
@pytest.mark.parametrize("n", [1, 2, 5, 8])
def test_finished_run_is_feasible_and_carries_a_complete_proof(generator, n):
    instance = generator(n, seed=13)
    solution, report = HeldKarpSolver().solve(instance)

    assert check(instance, solution).is_feasible
    assert report.status is SolveStatus.PROVEN_OPTIMAL_TSP
    assert report.stop_reason is StopReason.OPTIMAL
    assert report.best_lower_bound == report.objective_value
    assert report.nodes_created == projected_state_count(n - 1)
    assert report.distance_matrix_hash == instance.matrix.content_hash


def test_node_cap_preserves_a_feasible_incumbent_and_never_claims_proof():
    instance = random_asymmetric_tsp(9, seed=37)
    solution, report = HeldKarpSolver().solve(instance, Budget(max_nodes=3))

    assert check(instance, solution).is_feasible
    assert report.nodes_explored == 3
    assert report.stop_reason is StopReason.NODE_CAP
    assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
    assert report.best_lower_bound == 0
    assert not report.status.permits_word_optimal


def test_memory_preflight_stops_before_allocating_an_oversized_table():
    instance = random_euclidean_tsp(15, seed=9)  # 14 * 2^13 states
    projected_mb = (
        projected_state_count(14) * ESTIMATED_BYTES_PER_STATE / (1024 * 1024)
    )
    assert projected_mb > 1

    solution, report = HeldKarpSolver().solve(
        instance, Budget(max_memory_mb=1)
    )
    assert check(instance, solution).is_feasible
    assert report.stop_reason is StopReason.MEMORY_CAP
    assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
    assert report.nodes_explored == 0
    assert report.best_lower_bound == 0


def test_wall_clock_expiry_is_reported_as_an_interruption(monkeypatch):
    import core.exact.held_karp as module

    ticks = iter(i / 1000 for i in range(100))
    monkeypatch.setattr(module.time, "perf_counter", lambda: next(ticks))
    instance = random_asymmetric_tsp(8, seed=3)
    solution, report = HeldKarpSolver().solve(
        instance, Budget(wall_time_ms=1)
    )

    assert check(instance, solution).is_feasible
    assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
    assert report.stop_reason is StopReason.TIMEOUT
    assert report.best_lower_bound == 0


def test_realistic_size_guard_reports_the_projected_table_size():
    instance = random_euclidean_tsp(20, seed=1)  # 19 customers > default 18
    with pytest.raises(ValueError, match="state table"):
        HeldKarpSolver().solve(instance)


def test_refuses_non_tsp_instances():
    tsp = random_euclidean_tsp(5, seed=2)
    cvrp = Instance(
        name="fleet",
        stops=tsp.stops,
        vehicles=(Vehicle(0), Vehicle(1)),
        matrix=tsp.matrix,
    )
    with pytest.raises(ValueError, match="TSP only"):
        HeldKarpSolver().solve(cvrp)

