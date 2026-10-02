"""Constructive heuristics: nearest neighbour and Clarke-Wright savings."""

import pytest

from bench.generators import random_euclidean_tsp
from core.construct.nearest_neighbour import NearestNeighbourSolver
from core.construct.savings import ClarkeWrightSolver
from core.distance.matrix import DistanceMatrix
from core.eval.feasibility import check
from core.exact.brute_force import BruteForceSolver
from core.model.instance import Instance
from core.model.stop import Stop
from core.model.units import Unit
from core.model.vehicle import Vehicle
from core.reporting.status import SolveStatus

HEURISTICS = [NearestNeighbourSolver(), ClarkeWrightSolver()]


@pytest.mark.parametrize("solver", HEURISTICS, ids=lambda s: s.name)
@pytest.mark.parametrize("n", [4, 8, 15, 30])
def test_visits_every_customer_exactly_once(solver, n):
    instance = random_euclidean_tsp(n, seed=5)
    solution, _ = solver.solve(instance)
    assert check(instance, solution).is_feasible
    served = solution.served
    assert sorted(served) == sorted(instance.customer_indices)
    assert len(served) == len(set(served))


@pytest.mark.parametrize("solver", HEURISTICS, ids=lambda s: s.name)
@pytest.mark.parametrize("n", [4, 5, 6, 7])
def test_never_beats_the_proven_optimum(solver, n):
    """A heuristic scoring below the optimum would mean the objective is wrong."""
    instance = random_euclidean_tsp(n, seed=11)
    optimum = BruteForceSolver().solve(instance)[1].objective_value
    _, report = solver.solve(instance)
    assert report.objective_value >= optimum


@pytest.mark.parametrize("solver", HEURISTICS, ids=lambda s: s.name)
def test_never_claims_optimality(solver):
    _, report = solver.solve(random_euclidean_tsp(10, seed=1))
    assert not report.status.permits_word_optimal
    assert report.best_lower_bound is None


def test_nearest_neighbour_is_deterministic():
    instance = random_euclidean_tsp(20, seed=3)
    a = NearestNeighbourSolver().solve(instance)[1].objective_value
    b = NearestNeighbourSolver().solve(instance)[1].objective_value
    assert a == b


def test_nearest_neighbour_picks_the_nearest_first():
    # Depot at 0. Node 1 is far, node 2 is near.
    data = [
        0, 100, 10,
        100, 0, 50,
        10, 50, 0,
    ]
    matrix = DistanceMatrix(data, 3, Unit.METRES)
    instance = Instance.single_vehicle_tsp(
        "tiny", [Stop(id=i) for i in range(3)], matrix
    )
    solution, _ = NearestNeighbourSolver().solve(instance)
    assert solution.routes[0].sequence[0] == 2


def test_clarke_wright_respects_capacity():
    """Four customers of demand 3, capacity 6: no route may carry more than two."""
    n = 5
    data = [0] * (n * n)
    for i in range(n):
        for j in range(n):
            if i != j:
                data[i * n + j] = 10 + abs(i - j)
    matrix = DistanceMatrix(data, n, Unit.METRES)
    stops = tuple(Stop(id=i, demand=0 if i == 0 else 3) for i in range(n))
    instance = Instance(
        name="cap",
        stops=stops,
        vehicles=tuple(Vehicle(id=v, capacity=6) for v in range(4)),
        matrix=matrix,
    )
    solution, _ = ClarkeWrightSolver().solve(instance)
    for route in solution.routes:
        assert sum(instance.stops[c].demand for c in route.sequence) <= 6
    assert check(instance, solution).is_feasible


def test_clarke_wright_builds_one_route_when_capacity_is_unlimited():
    instance = random_euclidean_tsp(12, seed=4)
    solution, _ = ClarkeWrightSolver().solve(instance)
    assert len([r for r in solution.routes if not r.is_empty]) == 1


def test_clarke_wright_flags_infeasible_when_it_needs_more_vans_than_exist():
    n = 5
    data = [0] * (n * n)
    for i in range(n):
        for j in range(n):
            if i != j:
                data[i * n + j] = 10
    matrix = DistanceMatrix(data, n, Unit.METRES)
    stops = tuple(Stop(id=i, demand=0 if i == 0 else 5) for i in range(n))
    instance = Instance(
        name="tight",
        stops=stops,
        vehicles=(Vehicle(id=0, capacity=5),),   # one van, four full loads
        matrix=matrix,
    )
    _, report = ClarkeWrightSolver().solve(instance)
    assert report.status is SolveStatus.HEURISTIC_INFEASIBLE


@pytest.mark.parametrize("solver", HEURISTICS, ids=lambda s: s.name)
def test_report_carries_the_matrix_hash(solver):
    instance = random_euclidean_tsp(9, seed=2)
    _, report = solver.solve(instance)
    assert report.distance_matrix_hash == instance.matrix.content_hash
