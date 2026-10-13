"""Nearest-neighbour is deterministic, feasible, and never presented as exact."""

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.construct.nearest_neighbor import NearestNeighborSolver
from core.distance.matrix import DistanceMatrix
from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance
from core.model.stop import Stop
from core.model.units import Unit
from core.model.vehicle import Vehicle
from core.reporting.status import SolveStatus, StopReason
from core.solver import Budget


def _matrix_instance(data, n, *, depot=0, name="hand"):
    return Instance.single_vehicle_tsp(
        name,
        tuple(Stop(id=i) for i in range(n)),
        DistanceMatrix(data, n, Unit.TSPLIB),
        depot_index=depot,
    )


def test_follows_nearest_edges_and_closes_the_tour():
    # 0 -> 2 -> 3 -> 1 -> 0 is forced by the cheapest available edge at each
    # construction step.  The matrix is directed on purpose.
    instance = _matrix_instance(
        [
            0, 9, 1, 8,
            4, 0, 7, 6,
            9, 5, 0, 2,
            8, 1, 3, 0,
        ],
        4,
    )
    solution, report = NearestNeighborSolver().solve(instance)

    assert solution.routes[0].sequence == (2, 3, 1)
    assert report.objective_value == 1 + 2 + 1 + 4
    assert report.objective_value == solution_cost(instance, solution)
    assert check(instance, solution).is_feasible


def test_equal_cost_ties_are_broken_by_node_index():
    instance = _matrix_instance(
        [
            0, 1, 1, 1,
            1, 0, 1, 1,
            1, 1, 0, 1,
            1, 1, 1, 0,
        ],
        4,
    )
    solution, _ = NearestNeighborSolver().solve(instance)
    assert solution.routes[0].sequence == (1, 2, 3)


@pytest.mark.parametrize("generator", [random_euclidean_tsp, random_asymmetric_tsp])
@pytest.mark.parametrize("n", [1, 2, 5, 12])
@pytest.mark.parametrize("seed", [0, 7, 41])
def test_seeded_outputs_are_complete_and_independently_feasible(generator, n, seed):
    instance = generator(n, seed)
    solution, report = NearestNeighborSolver().solve(instance)

    assert check(instance, solution).is_feasible
    assert set(solution.served) == set(instance.customer_indices)
    assert report.status is SolveStatus.HEURISTIC_FEASIBLE_TSP
    assert report.stop_reason is StopReason.COMPLETED
    assert report.best_lower_bound is None
    assert not report.status.permits_word_optimal


def test_nonzero_depot_is_respected():
    instance = _matrix_instance(
        [
            0, 7, 3,
            2, 0, 1,
            4, 2, 0,
        ],
        3,
        depot=1,
    )
    solution, report = NearestNeighborSolver().solve(instance)
    assert solution.routes[0].sequence == (2, 0)
    assert report.objective_value == 1 + 4 + 7
    assert check(instance, solution).is_feasible


def test_node_budget_returns_a_complete_fallback_without_a_proof_claim():
    instance = random_asymmetric_tsp(10, seed=4)
    solution, report = NearestNeighborSolver().solve(
        instance, Budget(max_nodes=2)
    )

    assert check(instance, solution).is_feasible
    assert report.nodes_explored == 2
    assert report.stop_reason is StopReason.NODE_CAP
    assert report.status is SolveStatus.HEURISTIC_FEASIBLE_TSP
    assert report.best_lower_bound is None
    assert "optimal for this" not in report.headline()


def test_refuses_a_multi_vehicle_problem():
    tsp = random_euclidean_tsp(4, seed=2)
    cvrp = Instance(
        name="two vehicles",
        stops=tsp.stops,
        vehicles=(Vehicle(0), Vehicle(1)),
        matrix=tsp.matrix,
    )
    with pytest.raises(ValueError, match="TSP only"):
        NearestNeighborSolver().solve(cvrp)

