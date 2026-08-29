"""Claim discipline: a report that overstates its evidence must not be constructible."""

import pytest

from core.model.instance import ProblemType
from core.model.units import Unit
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason


def proven(**kw):
    base = dict(
        solver_name="test",
        problem_type=ProblemType.TSP,
        status=SolveStatus.PROVEN_OPTIMAL_TSP,
        stop_reason=StopReason.OPTIMAL,
        objective_value=100,
        objective_units=Unit.TSPLIB,
        best_lower_bound=100,
    )
    return SolveReport(**{**base, **kw})


def test_valid_proven_report_constructs():
    r = proven()
    assert r.status.permits_word_optimal
    assert r.proven_gap == 0.0
    assert "optimal" in r.headline()


def test_cannot_claim_optimal_after_a_timeout():
    with pytest.raises(ValueError, match="requires stop_reason=OPTIMAL"):
        proven(stop_reason=StopReason.TIMEOUT)


def test_cannot_claim_tsp_optimality_for_a_cvrptw_run():
    """A TSP certificate says nothing about a multi-vehicle plan."""
    with pytest.raises(ValueError, match="only valid for TSP"):
        proven(problem_type=ProblemType.CVRPTW)


def test_timeout_status_requires_a_lower_bound():
    with pytest.raises(ValueError, match="must carry best_lower_bound"):
        SolveReport(
            solver_name="bnb",
            problem_type=ProblemType.TSP,
            status=SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
            stop_reason=StopReason.TIMEOUT,
            objective_value=120,
            objective_units=Unit.TSPLIB,
        )


def test_reference_value_requires_provenance():
    with pytest.raises(ValueError, match="requires reference_source"):
        SolveReport(
            solver_name="alns",
            problem_type=ProblemType.CVRPTW,
            status=SolveStatus.HEURISTIC_FEASIBLE_CVRPTW,
            stop_reason=StopReason.COMPLETED,
            objective_value=500,
            objective_units=Unit.METRES,
            reference_value=480,
        )


def test_lower_bound_above_objective_is_rejected():
    """An invalid bound may already have pruned the optimum; refuse to record it."""
    with pytest.raises(ValueError, match="bound is invalid"):
        proven(best_lower_bound=101)


def test_reference_gap_is_named_separately_from_proven_gap():
    r = SolveReport(
        solver_name="sa",
        problem_type=ProblemType.CVRPTW,
        status=SolveStatus.HEURISTIC_FEASIBLE_CVRPTW,
        stop_reason=StopReason.COMPLETED,
        objective_value=1050,
        objective_units=Unit.METRES,
        reference_value=1000,
        reference_source="OR-Tools 9.10, GLS, 60s",
    )
    assert r.proven_gap is None              # no proof exists
    assert r.reference_gap == pytest.approx(0.05)
    assert "optimal" not in r.headline()
    assert "OR-Tools" in r.headline()


def test_headline_never_says_optimal_without_a_proof():
    for status in SolveStatus:
        if status.permits_word_optimal:
            continue
        kw = dict(
            solver_name="x",
            problem_type=ProblemType.CVRPTW,
            status=status,
            stop_reason=StopReason.COMPLETED,
            objective_value=10,
            objective_units=Unit.METRES,
        )
        if status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT:
            kw.update(problem_type=ProblemType.TSP, stop_reason=StopReason.TIMEOUT,
                      best_lower_bound=8)
        assert "optimal for this" not in SolveReport(**kw).headline()


def test_only_one_status_permits_the_word_optimal():
    permitting = [s for s in SolveStatus if s.permits_word_optimal]
    assert permitting == [SolveStatus.PROVEN_OPTIMAL_TSP]
