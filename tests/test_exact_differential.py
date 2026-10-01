"""Independent exact methods must agree on seeded symmetric and directed TSPs."""

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.distance.matrix import DistanceMatrix
from core.exact.branch_and_bound import BranchAndBoundSolver
from core.exact.brute_force import BruteForceSolver
from core.exact.held_karp import HeldKarpSolver
from core.model.instance import Instance
from core.model.stop import Stop
from core.model.units import Unit
from core.reporting.status import SolveStatus, StopReason
from core.solver import Budget


@pytest.mark.parametrize("generator", [random_euclidean_tsp, random_asymmetric_tsp])
@pytest.mark.parametrize("n", range(1, 9))
@pytest.mark.parametrize("seed", range(6))
def test_brute_force_held_karp_and_branch_and_bound_agree(generator, n, seed):
    instance = generator(n, seed)
    brute_solution, brute = BruteForceSolver().solve(instance)
    hk_solution, hk = HeldKarpSolver().solve(instance)
    bnb_solution, bnb = BranchAndBoundSolver().solve(instance)

    assert brute.objective_value == hk.objective_value == bnb.objective_value
    for solution, report in (
        (brute_solution, brute),
        (hk_solution, hk),
        (bnb_solution, bnb),
    ):
        assert check(instance, solution).is_feasible
        assert solution_cost(instance, solution) == report.objective_value
        assert report.status is SolveStatus.PROVEN_OPTIMAL_TSP
        assert report.stop_reason is StopReason.OPTIMAL
        assert report.best_lower_bound == report.objective_value


@pytest.mark.parametrize("solver", [HeldKarpSolver(), BranchAndBoundSolver()])
def test_bound_equal_to_incumbent_is_recognised_as_a_proof_even_at_node_cap(solver):
    matrix = DistanceMatrix([0] * 16, 4, Unit.TSPLIB)
    instance = Instance.single_vehicle_tsp(
        "zero costs", tuple(Stop(id=i) for i in range(4)), matrix
    )
    solution, report = solver.solve(instance, Budget(max_nodes=1))

    assert check(instance, solution).is_feasible
    assert report.objective_value == 0
    assert report.best_lower_bound == 0
    assert report.status is SolveStatus.PROVEN_OPTIMAL_TSP
    assert report.stop_reason is StopReason.OPTIMAL


def test_all_exact_methods_respect_a_nonzero_depot_index():
    matrix = DistanceMatrix(
        [
            0, 7, 4, 8,
            3, 0, 6, 2,
            5, 1, 0, 9,
            4, 3, 2, 0,
        ],
        4,
        Unit.TSPLIB,
    )
    instance = Instance.single_vehicle_tsp(
        "nonzero depot",
        tuple(Stop(id=i) for i in range(4)),
        matrix,
        depot_index=2,
    )

    reports = [
        solver.solve(instance)[1]
        for solver in (BruteForceSolver(), HeldKarpSolver(), BranchAndBoundSolver())
    ]
    assert len({report.objective_value for report in reports}) == 1
    assert all(report.status is SolveStatus.PROVEN_OPTIMAL_TSP for report in reports)
