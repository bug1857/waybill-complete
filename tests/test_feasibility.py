"""The independent checker must catch every constraint violation it exists for."""

import pytest

from bench.generators import random_euclidean_tsp
from core.distance.matrix import DistanceMatrix
from core.eval.feasibility import ViolationKind, check, schedule
from core.model.instance import Instance, ProblemType
from core.model.solution import Route, Solution
from core.model.stop import ANYTIME, Stop, TimeWindow
from core.model.units import Unit
from core.model.vehicle import Vehicle


def line_instance(**kw):
    """Depot at 0, three customers strung out at 100s intervals."""
    n = 4
    data = [0] * (n * n)
    for i in range(n):
        for j in range(n):
            if i != j:
                data[i * n + j] = abs(i - j) * 100
    matrix = DistanceMatrix(data, n, Unit.SECONDS)
    stops = kw.get("stops") or tuple(
        Stop(id=i, demand=0 if i == 0 else 1) for i in range(n)
    )
    vehicles = kw.get("vehicles") or (Vehicle(id=0, capacity=10),)
    return Instance(
        name="line", stops=stops, vehicles=vehicles, matrix=matrix, depot_index=0
    )


def test_valid_solution_is_feasible():
    inst = line_instance()
    report = check(inst, Solution((Route(0, (1, 2, 3)),)))
    assert report.is_feasible


def test_missing_customer_is_caught():
    inst = line_instance()
    report = check(inst, Solution((Route(0, (1, 2)),)))
    assert not report.is_feasible
    assert any(v.kind is ViolationKind.UNVISITED_CUSTOMER and v.node == 3
               for v in report.violations)


def test_explicitly_unserved_customer_marks_a_partial_solution_infeasible():
    inst = line_instance()
    report = check(inst, Solution((Route(0, (1, 2)),), unserved=frozenset({3})))
    assert not report.is_feasible
    assert any(
        v.kind is ViolationKind.UNSERVED_CUSTOMER and v.node == 3
        for v in report.violations
    )


def test_duplicate_visit_across_routes_is_caught():
    inst = line_instance(vehicles=(Vehicle(0, 10), Vehicle(1, 10)))
    report = check(inst, Solution((Route(0, (1, 2)), Route(1, (2, 3)))))
    assert any(v.kind is ViolationKind.DUPLICATE_VISIT for v in report.violations)


def test_depot_inside_route_is_caught():
    inst = line_instance()
    report = check(inst, Solution((Route(0, (1, 0, 2, 3)),)))
    assert any(v.kind is ViolationKind.DEPOT_IN_ROUTE for v in report.violations)


def test_capacity_exceeded_is_caught():
    inst = line_instance(vehicles=(Vehicle(id=0, capacity=2),))
    report = check(inst, Solution((Route(0, (1, 2, 3)),)))
    assert any(v.kind is ViolationKind.CAPACITY_EXCEEDED for v in report.violations)


def test_unknown_vehicle_is_caught():
    inst = line_instance()
    report = check(inst, Solution((Route(99, (1, 2, 3)),)))
    assert any(v.kind is ViolationKind.UNKNOWN_VEHICLE for v in report.violations)


def test_time_window_missed_is_caught():
    stops = (
        Stop(id=0),
        Stop(id=1, time_window=ANYTIME),
        Stop(id=2, time_window=TimeWindow(0, 150)),   # reachable only at 200s
        Stop(id=3, time_window=ANYTIME),
    )
    inst = line_instance(stops=stops)
    report = check(inst, Solution((Route(0, (1, 2, 3)),)))
    assert any(v.kind is ViolationKind.TIME_WINDOW_MISSED and v.node == 2
               for v in report.violations)


def test_early_arrival_waits_rather_than_violating():
    stops = (
        Stop(id=0),
        Stop(id=1, time_window=TimeWindow(5000, 9000)),
        Stop(id=2),
        Stop(id=3),
    )
    inst = line_instance(
        stops=stops, vehicles=(Vehicle(id=0, capacity=10, shift_end=100_000),)
    )
    report = check(inst, Solution((Route(0, (1, 2, 3)),)))
    assert report.is_feasible


def test_shift_end_exceeded_is_caught():
    inst = line_instance(vehicles=(Vehicle(id=0, capacity=10, shift_end=100),))
    report = check(inst, Solution((Route(0, (1, 2, 3)),)))
    assert any(v.kind is ViolationKind.SHIFT_EXCEEDED for v in report.violations)


def test_max_route_duration_exceeded_is_caught():
    inst = line_instance(
        vehicles=(Vehicle(id=0, capacity=10, max_route_duration=100),)
    )
    report = check(inst, Solution((Route(0, (1, 2, 3)),)))
    assert any(v.kind is ViolationKind.DURATION_EXCEEDED for v in report.violations)


def test_all_violations_are_collected_not_just_the_first():
    inst = line_instance(vehicles=(Vehicle(id=0, capacity=1, shift_end=50),))
    report = check(inst, Solution((Route(0, (1, 2)),)))
    kinds = {v.kind for v in report.violations}
    assert len(kinds) >= 2


def test_schedule_reconstructs_arrivals_and_waits():
    stops = (
        Stop(id=0),
        Stop(id=1, time_window=TimeWindow(500, 9000), service_time=30),
        Stop(id=2),
        Stop(id=3),
    )
    inst = line_instance(
        stops=stops, vehicles=(Vehicle(id=0, capacity=10, shift_end=100_000),)
    )
    sched = schedule(inst, Route(0, (1, 2, 3)), inst.vehicles[0])
    assert sched.arrival[0] == 100          # travel 0->1
    assert sched.wait[0] == 400             # waits until window opens at 500
    assert sched.departure[0] == 530        # 500 + 30s service


def test_raise_if_infeasible_lists_causes():
    inst = line_instance()
    report = check(inst, Solution((Route(0, (1, 2)),)))
    with pytest.raises(Exception, match="unvisited_customer"):
        report.raise_if_infeasible()


def test_tsp_solution_needs_no_time_source():
    """A pure TSP instance has no time constraints, so no time matrix is required."""
    inst = random_euclidean_tsp(6, seed=5)
    assert inst.problem_type is ProblemType.TSP
    assert not inst.has_time_constraints
    assert check(inst, Solution.single_tour((1, 2, 3, 4, 5))).is_feasible


def test_capacity_only_cvrp_does_not_require_a_time_matrix():
    n = 4
    matrix = DistanceMatrix(
        [0 if i == j else abs(i - j) * 100 for i in range(n) for j in range(n)],
        n,
        Unit.METRES,
    )
    inst = Instance(
        name="capacity-only",
        stops=tuple(Stop(id=i, demand=0 if i == 0 else 1) for i in range(n)),
        vehicles=(Vehicle(id=0, capacity=3),),
        matrix=matrix,
    )
    assert inst.problem_type is ProblemType.CVRP
    assert not inst.has_time_constraints
    assert check(inst, Solution((Route(0, (1, 2, 3)),))).is_feasible


@pytest.mark.parametrize("unserved", [frozenset({0}), frozenset({99})])
def test_depot_and_unknown_nodes_cannot_be_declared_unserved(unserved):
    inst = line_instance()
    report = check(inst, Solution((Route(0, (1, 2, 3)),), unserved=unserved))
    assert any(
        v.kind is ViolationKind.INVALID_UNSERVED_NODE for v in report.violations
    )


def test_a_node_cannot_be_both_served_and_unserved():
    with pytest.raises(ValueError, match="both served and unserved"):
        Solution((Route(0, (1, 2, 3)),), unserved=frozenset({3}))
