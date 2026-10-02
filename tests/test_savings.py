"""Clarke-Wright fleet construction and the named Phase 5 gate."""

from bench.generators import clustered_cvrptw_150
from core.construct.savings import ClarkeWrightSolver
from core.distance.matrix import DistanceMatrix
from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance
from core.model.solution import Solution
from core.model.stop import Stop, TimeWindow
from core.model.units import Unit
from core.model.vehicle import Vehicle
from core.reporting.status import SolveStatus, StopReason
from core.solver import Budget


def _small_instance(*, impossible: bool = False) -> Instance:
    matrix = DistanceMatrix(
        [
            0, 2, 2, 8, 8,
            2, 0, 1, 9, 9,
            2, 1, 0, 8, 9,
            8, 9, 8, 0, 1,
            8, 9, 9, 1, 0,
        ],
        5,
        Unit.METRES,
    )
    time_matrix = DistanceMatrix(
        [
            0, 2, 2, 8, 8,
            2, 0, 1, 9, 9,
            2, 1, 0, 8, 9,
            8, 9, 8, 0, 1,
            8, 9, 9, 1, 0,
        ],
        5,
        Unit.SECONDS,
    )
    demand = 2 if impossible else 1
    stops = (Stop(id=0),) + tuple(
        Stop(
            id=i,
            demand=demand,
            time_window=TimeWindow(0, 100),
            service_time=1,
        )
        for i in range(1, 5)
    )
    vehicles = (
        Vehicle(id=7, capacity=2, shift_end=100, max_route_duration=100),
        Vehicle(id=9, capacity=2, shift_end=100, max_route_duration=100),
    )
    return Instance(
        name="small-cvrptw",
        stops=stops,
        vehicles=vehicles,
        matrix=matrix,
        time_matrix=time_matrix,
    )


def test_savings_builds_complete_feasible_fleet_plan() -> None:
    instance = _small_instance()

    solution, report = ClarkeWrightSolver().solve(instance)

    assert check(instance, solution).is_feasible
    assert solution.unserved == frozenset()
    assert solution.used_vehicle_count == 2
    assert {route.vehicle_id for route in solution.routes} == {7, 9}
    assert report.status is SolveStatus.HEURISTIC_FEASIBLE_CVRPTW
    assert report.stop_reason is StopReason.COMPLETED
    assert report.objective_value == solution_cost(instance, solution)
    assert report.best_lower_bound is None


def test_savings_is_deterministic() -> None:
    instance = _small_instance()
    solver = ClarkeWrightSolver()

    first_solution, first_report = solver.solve(instance)
    second_solution, second_report = solver.solve(instance)

    assert first_solution == second_solution
    assert first_report.objective_value == second_report.objective_value
    assert first_report.extra == second_report.extra


def test_savings_reports_completed_infeasible_candidate_without_proving_instance() -> None:
    instance = _small_instance(impossible=True)

    solution, report = ClarkeWrightSolver().solve(instance)

    assert not check(instance, solution).is_feasible
    assert solution.unserved
    assert report.status is SolveStatus.HEURISTIC_INFEASIBLE
    assert report.stop_reason is StopReason.INFEASIBLE
    assert report.extra["instance_infeasibility_proven"] == "false"


def test_savings_reports_budget_interruption_as_partial() -> None:
    instance = _small_instance()

    solution, report = ClarkeWrightSolver().solve(
        instance, Budget(max_nodes=1)
    )

    assert isinstance(solution, Solution)
    assert solution.unserved
    assert report.status is SolveStatus.HEURISTIC_PARTIAL
    assert report.stop_reason is StopReason.NODE_CAP
    assert "partial" in report.headline().lower()


def test_named_150_customer_six_vehicle_gate() -> None:
    instance = clustered_cvrptw_150()

    solution, report = ClarkeWrightSolver().solve(instance)

    feasibility = check(instance, solution)
    assert feasibility.is_feasible, "\n".join(map(str, feasibility.violations))
    assert instance.n == 151  # depot plus 150 delivery stops
    assert solution.used_vehicle_count == 6
    assert len(solution.served) == 150
    assert set(solution.served) == set(instance.customer_indices)
    assert report.status is SolveStatus.HEURISTIC_FEASIBLE_CVRPTW
    assert report.stop_reason is StopReason.COMPLETED
    assert report.distance_matrix_hash == instance.matrix.content_hash
