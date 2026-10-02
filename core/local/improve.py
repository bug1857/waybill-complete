"""Deterministic local improvement with independent feasibility checks.

Or-opt relocates an ordered segment without reversing it and is therefore valid
for both symmetric and asymmetric matrices. Classical 2-opt reverses a segment;
this implementation deliberately refuses asymmetric matrices instead of using
the invalid four-edge delta commonly copied from symmetric TSP code.
"""

from dataclasses import dataclass

from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance
from core.model.solution import Route, Solution


@dataclass(frozen=True, slots=True)
class LocalSearchStats:
    initial_cost: int
    final_cost: int
    passes: int
    moves_evaluated: int
    accepted_moves: int
    infeasible_moves_rejected: int


@dataclass(frozen=True, slots=True)
class LocalSearchResult:
    solution: Solution
    stats: LocalSearchStats


def _require_feasible(instance: Instance, solution: Solution) -> None:
    report = check(instance, solution)
    if not report.is_feasible:
        report.raise_if_infeasible()


def _replace_route(
    solution: Solution,
    route_index: int,
    sequence: tuple[int, ...],
) -> Solution:
    routes = list(solution.routes)
    original = routes[route_index]
    routes[route_index] = Route(original.vehicle_id, sequence)
    return Solution(tuple(routes), solution.unserved)


def two_opt_descent(
    instance: Instance,
    initial: Solution,
    *,
    max_passes: int | None = None,
) -> LocalSearchResult:
    """Run best-improvement 2-opt on each route of a symmetric instance."""
    if not instance.matrix.is_symmetric:
        raise ValueError(
            "classical 2-opt requires a symmetric matrix because it reverses "
            "internal edges; use or_opt_descent for asymmetric costs"
        )
    if max_passes is not None and max_passes <= 0:
        raise ValueError("max_passes must be positive when set")
    _require_feasible(instance, initial)

    current = initial
    initial_cost = solution_cost(instance, current)
    current_cost = initial_cost
    passes = 0
    evaluated = 0
    accepted = 0
    infeasible = 0

    while max_passes is None or passes < max_passes:
        passes += 1
        best_solution: Solution | None = None
        best_cost = current_cost

        for route_index, route in enumerate(current.routes):
            sequence = route.sequence
            for start in range(len(sequence) - 1):
                for end in range(start + 1, len(sequence)):
                    candidate_sequence = (
                        sequence[:start]
                        + tuple(reversed(sequence[start : end + 1]))
                        + sequence[end + 1 :]
                    )
                    if candidate_sequence == sequence:
                        continue
                    candidate = _replace_route(
                        current, route_index, candidate_sequence
                    )
                    evaluated += 1
                    candidate_cost = solution_cost(instance, candidate)
                    if candidate_cost >= best_cost:
                        continue
                    if not check(instance, candidate).is_feasible:
                        infeasible += 1
                        continue
                    best_solution = candidate
                    best_cost = candidate_cost

        if best_solution is None:
            break
        current = best_solution
        current_cost = best_cost
        accepted += 1

    return LocalSearchResult(
        current,
        LocalSearchStats(
            initial_cost=initial_cost,
            final_cost=current_cost,
            passes=passes,
            moves_evaluated=evaluated,
            accepted_moves=accepted,
            infeasible_moves_rejected=infeasible,
        ),
    )


def _relocated_candidate(
    solution: Solution,
    *,
    source_route: int,
    segment_start: int,
    segment_length: int,
    destination_route: int,
    insertion_position: int,
) -> Solution | None:
    """Return one ordered segment relocation, or ``None`` for a no-op."""
    routes = list(solution.routes)
    source = routes[source_route]
    segment_end = segment_start + segment_length
    segment = source.sequence[segment_start:segment_end]
    source_remaining = (
        source.sequence[:segment_start] + source.sequence[segment_end:]
    )

    if source_route == destination_route:
        destination_sequence = source_remaining
        candidate_sequence = (
            destination_sequence[:insertion_position]
            + segment
            + destination_sequence[insertion_position:]
        )
        if candidate_sequence == source.sequence:
            return None
        routes[source_route] = Route(source.vehicle_id, candidate_sequence)
    else:
        destination = routes[destination_route]
        candidate_destination = (
            destination.sequence[:insertion_position]
            + segment
            + destination.sequence[insertion_position:]
        )
        routes[source_route] = Route(source.vehicle_id, source_remaining)
        routes[destination_route] = Route(
            destination.vehicle_id, candidate_destination
        )

    return Solution(tuple(routes), solution.unserved)


def or_opt_descent(
    instance: Instance,
    initial: Solution,
    *,
    max_segment_length: int = 3,
    max_passes: int | None = None,
) -> LocalSearchResult:
    """Relocate ordered segments within or between routes until locally optimal.

    Candidate solutions are checked by the independent feasibility engine before
    acceptance, so capacity and time constraints remain hard throughout search.
    """
    if max_segment_length <= 0:
        raise ValueError("max_segment_length must be positive")
    if max_passes is not None and max_passes <= 0:
        raise ValueError("max_passes must be positive when set")
    _require_feasible(instance, initial)

    current = initial
    initial_cost = solution_cost(instance, current)
    current_cost = initial_cost
    passes = 0
    evaluated = 0
    accepted = 0
    infeasible = 0

    while max_passes is None or passes < max_passes:
        passes += 1
        best_solution: Solution | None = None
        best_cost = current_cost

        for source_index, source in enumerate(current.routes):
            maximum = min(max_segment_length, len(source.sequence))
            for length in range(1, maximum + 1):
                for start in range(len(source.sequence) - length + 1):
                    for destination_index, destination in enumerate(current.routes):
                        destination_length = (
                            len(source.sequence) - length
                            if source_index == destination_index
                            else len(destination.sequence)
                        )
                        for insertion in range(destination_length + 1):
                            candidate = _relocated_candidate(
                                current,
                                source_route=source_index,
                                segment_start=start,
                                segment_length=length,
                                destination_route=destination_index,
                                insertion_position=insertion,
                            )
                            if candidate is None:
                                continue
                            evaluated += 1
                            candidate_cost = solution_cost(instance, candidate)
                            if candidate_cost >= best_cost:
                                continue
                            if not check(instance, candidate).is_feasible:
                                infeasible += 1
                                continue
                            best_solution = candidate
                            best_cost = candidate_cost

        if best_solution is None:
            break
        current = best_solution
        current_cost = best_cost
        accepted += 1

    return LocalSearchResult(
        current,
        LocalSearchStats(
            initial_cost=initial_cost,
            final_cost=current_cost,
            passes=passes,
            moves_evaluated=evaluated,
            accepted_moves=accepted,
            infeasible_moves_rejected=infeasible,
        ),
    )
