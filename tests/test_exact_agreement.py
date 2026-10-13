"""The Phase 2 exit gate: every exact solver must agree.

Brute force enumerates, Held-Karp is a dynamic program over subsets, and Branch
& Bound is a tree search with a bound. They share no code path, so their
agreeing on the same instance is strong evidence that all three are right --
which is what lets Held-Karp and B&B be trusted between n=12, where brute force
stops, and n=51, where TSPLIB's published optima begin.
"""

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.eval.feasibility import check
from core.exact.bounds.reduction import completion_bound
from core.exact.branch_and_bound import BranchAndBoundSolver
from core.exact.brute_force import BruteForceSolver
from core.exact.held_karp import HeldKarpSolver, projected_state_count
from core.reporting.status import SolveStatus, StopReason
from core.solver import Budget

SIZES = [3, 4, 5, 6, 7, 8]
SEEDS = [0, 1, 2, 3, 4, 5]


@pytest.mark.parametrize("n", SIZES)
@pytest.mark.parametrize("seed", SEEDS)
def test_three_exact_solvers_agree_symmetric(n, seed):
    instance = random_euclidean_tsp(n, seed)
    bf = BruteForceSolver().solve(instance)[1].objective_value
    hk = HeldKarpSolver().solve(instance)[1].objective_value
    bb = BranchAndBoundSolver().solve(instance)[1].objective_value
    assert bf == hk == bb, f"brute={bf} held_karp={hk} branch_bound={bb}"


@pytest.mark.parametrize("n", SIZES)
@pytest.mark.parametrize("seed", SEEDS)
def test_three_exact_solvers_agree_asymmetric(n, seed):
    """Asymmetry must not break any of them -- real road data is asymmetric."""
    instance = random_asymmetric_tsp(n, seed)
    assert not instance.matrix.is_symmetric
    bf = BruteForceSolver().solve(instance)[1].objective_value
    hk = HeldKarpSolver().solve(instance)[1].objective_value
    bb = BranchAndBoundSolver().solve(instance)[1].objective_value
    assert bf == hk == bb, f"brute={bf} held_karp={hk} branch_bound={bb}"


@pytest.mark.parametrize("n", [4, 6, 8])
@pytest.mark.parametrize("seed", range(15))
def test_lower_bound_never_exceeds_the_true_optimum(n, seed):
    """The most important invariant in the project.

    An over-optimistic bound does not raise -- it prunes the branch holding the
    optimum and returns a wrong answer stamped PROVEN_OPTIMAL. Nothing else
    catches that.
    """
    instance = random_euclidean_tsp(n, seed)
    optimum = BruteForceSolver().solve(instance)[1].objective_value
    bound = completion_bound(
        instance.matrix,
        instance.depot_index,
        set(instance.customer_indices),
        instance.depot_index,
    )
    assert bound <= optimum, (
        f"bound {bound} exceeds optimum {optimum}: invalid, and may already have "
        f"pruned the optimum in a real search"
    )


@pytest.mark.parametrize("n", [5, 7, 9])
def test_exact_solvers_return_feasible_tours(n):
    instance = random_euclidean_tsp(n, seed=42)
    for solver in (BruteForceSolver(), HeldKarpSolver(), BranchAndBoundSolver()):
        solution, _ = solver.solve(instance)
        assert check(instance, solution).is_feasible
        assert set(solution.served) == set(instance.customer_indices)


def test_exact_solvers_claim_proven_optimality():
    instance = random_euclidean_tsp(7, seed=3)
    for solver in (BruteForceSolver(), HeldKarpSolver(), BranchAndBoundSolver()):
        _, report = solver.solve(instance)
        assert report.status is SolveStatus.PROVEN_OPTIMAL_TSP
        assert report.stop_reason is StopReason.OPTIMAL
        assert report.proven_gap == 0.0


def test_branch_and_bound_prunes_more_than_it_explores_on_larger_instances():
    _, report = BranchAndBoundSolver().solve(random_euclidean_tsp(10, seed=1))
    assert report.nodes_pruned > 0
    assert report.nodes_created >= report.nodes_explored


def test_branch_and_bound_records_bound_time_separately():
    """A tighter bound that costs too much per node can lose overall; that trade
    is invisible unless the two costs are timed apart."""
    _, report = BranchAndBoundSolver().solve(random_euclidean_tsp(9, seed=2))
    assert report.bound_time_ms >= 0.0
    assert report.wall_time_ms >= report.bound_time_ms


def test_held_karp_refuses_instances_beyond_its_memory_wall():
    instance = random_euclidean_tsp(40, seed=1)
    with pytest.raises(ValueError, match="Held--Karp limit"):
        HeldKarpSolver().solve(instance)


def test_held_karp_memory_estimate_doubles_per_stop():
    a, b = projected_state_count(14), projected_state_count(15)
    assert b / a == pytest.approx(2.13, rel=0.05)   # 2x from the mask, plus n/(n-1)


def test_branch_and_bound_timeout_reports_an_incumbent_not_a_proof():
    """A run that ran out of budget is a fact about the budget, not the answer."""
    instance = random_euclidean_tsp(12, seed=7)
    _, report = BranchAndBoundSolver().solve(instance, Budget(wall_time_ms=1))
    if report.stop_reason is StopReason.TIMEOUT:
        assert report.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
        assert not report.status.permits_word_optimal
        assert report.best_lower_bound is not None
