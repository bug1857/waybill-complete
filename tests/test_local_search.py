"""Correctness and instrumentation tests for local-search operators."""

from core.distance.matrix import DistanceMatrix
from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.local.improve import or_opt_descent, two_opt_descent
from core.local.annealing import AnnealingConfig, simulated_annealing
from core.model.instance import Instance
from core.model.solution import Route, Solution
from core.model.stop import Stop, TimeWindow
from core.model.units import Unit
from core.model.vehicle import Vehicle


def _instance(
    rows: list[list[int]],
    *,
    vehicles: tuple[Vehicle, ...] = (Vehicle(id=0),),
    stops: tuple[Stop, ...] | None = None,
    time_rows: list[list[int]] | None = None,
) -> Instance:
    n = len(rows)
    matrix = DistanceMatrix(
        [value for row in rows for value in row], n, Unit.METRES
    )
    time_matrix = None
    if time_rows is not None:
        time_matrix = DistanceMatrix(
            [value for row in time_rows for value in row], n, Unit.SECONDS
        )
    return Instance(
        name="local-search-fixture",
        stops=stops or tuple(Stop(id=i) for i in range(n)),
        vehicles=vehicles,
        matrix=matrix,
        time_matrix=time_matrix,
    )


def test_two_opt_removes_a_crossing_on_symmetric_matrix() -> None:
    # Tour 0-1-3-2-0 costs 22; reversing (3,2) gives cost 4.
    instance = _instance(
        [
            [0, 1, 1, 10],
            [1, 0, 10, 1],
            [1, 10, 0, 1],
            [10, 1, 1, 0],
        ]
    )
    initial = Solution.single_tour((1, 2, 3))

    result = two_opt_descent(instance, initial)

    assert check(instance, result.solution).is_feasible
    assert solution_cost(instance, result.solution) == 4
    assert result.stats.accepted_moves >= 1
    assert result.stats.final_cost < result.stats.initial_cost


def test_two_opt_refuses_asymmetric_matrix() -> None:
    instance = _instance(
        [
            [0, 1, 4, 2],
            [7, 0, 1, 3],
            [2, 8, 0, 1],
            [1, 5, 9, 0],
        ]
    )
    initial = Solution.single_tour((1, 2, 3))

    try:
        two_opt_descent(instance, initial)
    except ValueError as exc:
        assert "symmetric" in str(exc).lower()
    else:
        raise AssertionError("2-opt silently ran on an asymmetric matrix")


def test_or_opt_improves_asymmetric_tour_without_reversal() -> None:
    # Moving node 3 between 1 and 2 changes 0-1-2-3-0 (103) into
    # 0-1-3-2-0 (4). The matrix is deliberately directed.
    instance = _instance(
        [
            [0, 1, 1, 40],
            [9, 0, 1, 1],
            [1, 9, 0, 1],
            [60, 7, 1, 0],
        ]
    )
    initial = Solution.single_tour((1, 2, 3))

    result = or_opt_descent(instance, initial, max_segment_length=1)

    assert check(instance, result.solution).is_feasible
    assert result.solution.routes[0].sequence == (1, 3, 2)
    assert solution_cost(instance, result.solution) == 4


def test_or_opt_rejects_cheaper_but_time_window_infeasible_move() -> None:
    stops = (
        Stop(id=0),
        Stop(id=1, time_window=TimeWindow(0, 4)),
        Stop(id=2, time_window=TimeWindow(4, 20)),
    )
    vehicle = Vehicle(id=0, shift_end=30)
    # Cost prefers 0-2-1-0, while travel time makes node 1 late in that order.
    instance = _instance(
        [[0, 5, 1], [1, 0, 1], [1, 1, 0]],
        vehicles=(vehicle,),
        stops=stops,
        time_rows=[[0, 2, 1], [1, 0, 1], [1, 5, 0]],
    )
    initial = Solution.single_tour((1, 2))
    assert check(instance, initial).is_feasible

    result = or_opt_descent(instance, initial, max_segment_length=1)

    assert result.solution == initial
    assert check(instance, result.solution).is_feasible


def test_or_opt_can_move_between_vehicle_routes() -> None:
    vehicles = (Vehicle(id=10, capacity=2), Vehicle(id=20, capacity=2))
    stops = (
        Stop(id=0),
        Stop(id=1, demand=1),
        Stop(id=2, demand=1),
        Stop(id=3, demand=1),
    )
    instance = _instance(
        [
            [0, 1, 1, 1],
            [1, 0, 50, 1],
            [1, 50, 0, 1],
            [1, 1, 1, 0],
        ],
        vehicles=vehicles,
        stops=stops,
    )
    initial = Solution((Route(10, (1, 2)), Route(20, (3,))))
    assert check(instance, initial).is_feasible

    result = or_opt_descent(instance, initial, max_segment_length=1)

    assert check(instance, result.solution).is_feasible
    assert solution_cost(instance, result.solution) < solution_cost(instance, initial)
    assert {node for route in result.solution.routes for node in route.sequence} == {
        1,
        2,
        3,
    }


def test_simulated_annealing_is_seeded_and_records_real_acceptance() -> None:
    instance = _instance(
        [
            [0, 7, 3, 9, 4, 8],
            [5, 0, 6, 2, 9, 3],
            [8, 4, 0, 7, 2, 6],
            [3, 9, 5, 0, 8, 1],
            [6, 2, 7, 4, 0, 5],
            [1, 8, 3, 6, 9, 0],
        ]
    )
    initial = Solution.single_tour((1, 2, 3, 4, 5))
    config = AnnealingConfig(
        iterations=400,
        initial_temperature=1_000.0,
        cooling_rate=0.995,
        trace_every=25,
    )

    first = simulated_annealing(instance, initial, seed=817, config=config)
    second = simulated_annealing(instance, initial, seed=817, config=config)

    assert first.solution == second.solution
    assert first.stats == second.stats
    assert check(instance, first.solution).is_feasible
    assert first.stats.moves_proposed == config.iterations
    assert first.stats.moves_accepted > 0
    assert first.stats.accepted_worsening_moves > 0
    assert first.stats.best_trace[0][0] == 0
    assert first.stats.best_trace[-1][0] == config.iterations


def test_simulated_annealing_never_surfaces_an_infeasible_candidate() -> None:
    stops = (
        Stop(id=0),
        Stop(id=1, demand=1, time_window=TimeWindow(0, 4)),
        Stop(id=2, demand=1, time_window=TimeWindow(4, 20)),
        Stop(id=3, demand=1, time_window=TimeWindow(0, 20)),
    )
    instance = _instance(
        [
            [0, 3, 1, 2],
            [2, 0, 1, 1],
            [1, 2, 0, 1],
            [2, 1, 1, 0],
        ],
        vehicles=(Vehicle(id=0, capacity=3, shift_end=30),),
        stops=stops,
        time_rows=[
            [0, 2, 1, 2],
            [2, 0, 1, 1],
            [1, 5, 0, 1],
            [2, 1, 1, 0],
        ],
    )
    initial = Solution.single_tour((1, 2, 3))
    assert check(instance, initial).is_feasible

    result = simulated_annealing(
        instance,
        initial,
        seed=11,
        config=AnnealingConfig(iterations=200, initial_temperature=100.0),
    )

    assert check(instance, result.solution).is_feasible
    assert result.stats.infeasible_moves_rejected > 0
