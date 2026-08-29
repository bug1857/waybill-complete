"""Brute force is ground truth, so it is checked against an even simpler reference.

The reference below applies *no* symmetry reduction at all. Comparing the two
directly is what distinguishes a valid reduction (skipping a tour's reverse,
which costs the same) from an invalid one (fixing which customer is visited
first, which discards genuine tours). An earlier version of the solver made
exactly that mistake and enumerated 2 of 3 distinct tours on a 3-customer
instance; this test fails loudly on it.
"""

from itertools import permutations

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.distance.matrix import DistanceMatrix
from core.eval.feasibility import check
from core.exact.brute_force import BruteForceSolver
from core.model.instance import Instance
from core.model.stop import Stop
from core.model.units import Unit
from core.reporting.status import SolveStatus, StopReason


def exhaustive_reference(instance: Instance) -> int:
    """Cheapest tour, by enumerating every permutation with no reduction."""
    depot = instance.depot_index
    m = instance.matrix
    customers = instance.customer_indices
    if not customers:
        return 0
    best = None
    for perm in permutations(customers):
        cost = m.cost(depot, perm[0])
        for a, b in zip(perm, perm[1:]):
            cost += m.cost(a, b)
        cost += m.cost(perm[-1], depot)
        best = cost if best is None else min(best, cost)
    return best


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7])
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_matches_unreduced_reference_symmetric(n, seed):
    instance = random_euclidean_tsp(n, seed)
    assert instance.matrix.is_symmetric
    _, report = BruteForceSolver().solve(instance)
    assert report.objective_value == exhaustive_reference(instance)


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7])
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_matches_unreduced_reference_asymmetric(n, seed):
    """The reversal reduction must switch itself off when d(i,j) != d(j,i)."""
    instance = random_asymmetric_tsp(n, seed)
    assert not instance.matrix.is_symmetric
    _, report = BruteForceSolver().solve(instance)
    assert report.objective_value == exhaustive_reference(instance)


def test_symmetric_reduction_halves_the_work_without_changing_the_answer():
    sym = random_euclidean_tsp(7, seed=11)
    asym = random_asymmetric_tsp(7, seed=11)
    _, sym_report = BruteForceSolver().solve(sym)
    _, asym_report = BruteForceSolver().solve(asym)
    # 6 customers -> 720 permutations; symmetric explores half.
    assert asym_report.nodes_explored == 720
    assert sym_report.nodes_explored == 360


def test_hand_computable_square():
    """Four corners of a 10x10 square: the optimal tour is the perimeter, 40."""
    data = [
        0, 10, 14, 10,
        10, 0, 10, 14,
        14, 10, 0, 10,
        10, 14, 10, 0,
    ]
    matrix = DistanceMatrix(data, 4, Unit.TSPLIB)
    instance = Instance.single_vehicle_tsp(
        "square", [Stop(id=i) for i in range(4)], matrix
    )
    solution, report = BruteForceSolver().solve(instance)
    assert report.objective_value == 40
    assert check(instance, solution).is_feasible


def test_returns_a_feasible_solution_visiting_every_customer():
    instance = random_euclidean_tsp(7, seed=99)
    solution, _ = BruteForceSolver().solve(instance)
    assert check(instance, solution).is_feasible
    assert set(solution.served) == set(instance.customer_indices)


def test_report_claims_proven_optimality_correctly():
    instance = random_euclidean_tsp(6, seed=3)
    _, report = BruteForceSolver().solve(instance)
    assert report.status is SolveStatus.PROVEN_OPTIMAL_TSP
    assert report.stop_reason is StopReason.OPTIMAL
    assert report.status.permits_word_optimal
    assert report.best_lower_bound == report.objective_value
    assert report.proven_gap == 0.0
    assert report.distance_matrix_hash == instance.matrix.content_hash


def test_refuses_instances_above_its_limit():
    instance = random_euclidean_tsp(30, seed=1)
    with pytest.raises(ValueError, match="brute-force limit"):
        BruteForceSolver().solve(instance)


def test_single_node_instance():
    matrix = DistanceMatrix([0], 1, Unit.TSPLIB)
    instance = Instance.single_vehicle_tsp("solo", [Stop(id=0)], matrix)
    _, report = BruteForceSolver().solve(instance)
    assert report.objective_value == 0
