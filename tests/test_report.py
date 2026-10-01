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


def test_timeout_status_requires_an_interruption_reason():
    with pytest.raises(ValueError, match="interruption stop reason"):
        SolveReport(
            solver_name="bnb",
            problem_type=ProblemType.TSP,
            status=SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
            stop_reason=StopReason.COMPLETED,
            objective_value=120,
            objective_units=Unit.TSPLIB,
            best_lower_bound=100,
        )


def test_node_cap_is_a_valid_exact_interruption_reason():
    report = SolveReport(
        solver_name="bnb",
        problem_type=ProblemType.TSP,
        status=SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
        stop_reason=StopReason.NODE_CAP,
        objective_value=120,
        objective_units=Unit.TSPLIB,
        best_lower_bound=100,
    )
    assert report.proven_gap == pytest.approx(1 / 6)


def test_closed_exact_bound_cannot_be_labeled_unproven():
    with pytest.raises(ValueError, match="is proven"):
        SolveReport(
            solver_name="bnb",
            problem_type=ProblemType.TSP,
            status=SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
            stop_reason=StopReason.NODE_CAP,
            objective_value=100,
            objective_units=Unit.TSPLIB,
            best_lower_bound=100,
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


def test_reference_only_status_requires_a_named_reference():
    with pytest.raises(ValueError, match="requires a named reference"):
        SolveReport(
            solver_name="nn",
            problem_type=ProblemType.TSP,
            status=SolveStatus.REFERENCE_GAP_ONLY,
            stop_reason=StopReason.COMPLETED,
            objective_value=500,
            objective_units=Unit.METRES,
        )


def test_reference_source_without_value_is_rejected():
    with pytest.raises(ValueError, match="reference_source requires"):
        SolveReport(
            solver_name="nn",
            problem_type=ProblemType.TSP,
            status=SolveStatus.REFERENCE_GAP_ONLY,
            stop_reason=StopReason.COMPLETED,
            objective_value=500,
            objective_units=Unit.METRES,
            reference_source="published",
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
        elif status is SolveStatus.HEURISTIC_FEASIBLE_TSP:
            kw.update(problem_type=ProblemType.TSP)
        elif status is SolveStatus.HEURISTIC_INFEASIBLE:
            kw.update(stop_reason=StopReason.INFEASIBLE)
        elif status is SolveStatus.HEURISTIC_PARTIAL:
            kw.update(stop_reason=StopReason.TIMEOUT)
        elif status is SolveStatus.REFERENCE_GAP_ONLY:
            kw.update(reference_value=9, reference_source="named comparator")
        assert "optimal for this" not in SolveReport(**kw).headline()


def test_only_one_status_permits_the_word_optimal():
    permitting = [s for s in SolveStatus if s.permits_word_optimal]
    assert permitting == [SolveStatus.PROVEN_OPTIMAL_TSP]


def test_proven_status_requires_a_closed_bound():
    with pytest.raises(ValueError, match="best_lower_bound to equal"):
        proven(best_lower_bound=99)


def test_optimal_stop_reason_cannot_be_attached_to_a_non_proven_status():
    with pytest.raises(ValueError, match="requires status=PROVEN"):
        SolveReport(
            solver_name="nn",
            problem_type=ProblemType.TSP,
            status=SolveStatus.REFERENCE_GAP_ONLY,
            stop_reason=StopReason.OPTIMAL,
            objective_value=100,
            objective_units=Unit.TSPLIB,
            reference_value=90,
            reference_source="published",
        )


def test_timeout_headline_describes_bound_gap_without_claiming_distance_to_optimum():
    report = SolveReport(
        solver_name="bnb",
        problem_type=ProblemType.TSP,
        status=SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
        stop_reason=StopReason.TIMEOUT,
        objective_value=100,
        objective_units=Unit.TSPLIB,
        best_lower_bound=80,
    )
    headline = report.headline()
    assert "20.00% incumbent-relative gap to lower bound" in headline
    assert "within" not in headline


def test_cvrptw_feasible_status_cannot_label_a_tsp():
    with pytest.raises(ValueError, match="only valid for CVRPTW"):
        SolveReport(
            solver_name="savings",
            problem_type=ProblemType.TSP,
            status=SolveStatus.HEURISTIC_FEASIBLE_CVRPTW,
            stop_reason=StopReason.COMPLETED,
            objective_value=100,
            objective_units=Unit.METRES,
        )


def test_feasible_tsp_status_is_honest_and_problem_specific():
    report = SolveReport(
        solver_name="nearest_neighbour",
        problem_type=ProblemType.TSP,
        status=SolveStatus.HEURISTIC_FEASIBLE_TSP,
        stop_reason=StopReason.COMPLETED,
        objective_value=100,
        objective_units=Unit.METRES,
    )
    assert report.status.is_feasible
    assert "feasible TSP tour" in report.headline()
    assert "not proven optimal" in report.headline()


def test_feasible_tsp_status_cannot_label_a_cvrptw_plan():
    with pytest.raises(ValueError, match="only valid for TSP"):
        SolveReport(
            solver_name="nearest_neighbour",
            problem_type=ProblemType.CVRPTW,
            status=SolveStatus.HEURISTIC_FEASIBLE_TSP,
            stop_reason=StopReason.COMPLETED,
            objective_value=100,
            objective_units=Unit.METRES,
        )


def test_integer_counters_reject_booleans():
    with pytest.raises(TypeError, match="nodes_explored must be an integer"):
        proven(nodes_explored=True)


def test_partial_heuristic_is_non_feasible_and_requires_interruption():
    report = SolveReport(
        solver_name="fleet_builder",
        problem_type=ProblemType.CVRPTW,
        status=SolveStatus.HEURISTIC_PARTIAL,
        stop_reason=StopReason.TIMEOUT,
        objective_value=400,
        objective_units=Unit.METRES,
    )
    assert not report.status.is_feasible
    assert "partial incumbent" in report.headline()
    assert "infeasible instance" not in report.headline()

    with pytest.raises(ValueError, match="interruption stop reason"):
        SolveReport(
            solver_name="fleet_builder",
            problem_type=ProblemType.CVRPTW,
            status=SolveStatus.HEURISTIC_PARTIAL,
            stop_reason=StopReason.COMPLETED,
            objective_value=400,
            objective_units=Unit.METRES,
        )


def test_infeasible_candidate_headline_does_not_claim_instance_infeasibility():
    report = SolveReport(
        solver_name="fleet_builder",
        problem_type=ProblemType.CVRPTW,
        status=SolveStatus.HEURISTIC_INFEASIBLE,
        stop_reason=StopReason.INFEASIBLE,
        objective_value=400,
        objective_units=Unit.METRES,
    )
    assert not report.status.is_feasible
    assert report.headline().startswith("candidate infeasible")
    assert "not proof" in report.headline()


def test_partial_candidate_cannot_report_a_reference_gap():
    with pytest.raises(ValueError, match="cannot carry a reference gap"):
        SolveReport(
            solver_name="fleet_builder",
            problem_type=ProblemType.CVRPTW,
            status=SolveStatus.HEURISTIC_PARTIAL,
            stop_reason=StopReason.TIMEOUT,
            objective_value=400,
            objective_units=Unit.METRES,
            reference_value=350,
            reference_source="complete comparator",
        )
