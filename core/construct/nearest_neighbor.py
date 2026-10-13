"""Deterministic nearest-neighbour construction for TSP.

The implementation is intentionally small: from the current node, visit the
cheapest unvisited customer, breaking equal-cost ties by node index.  The depot
is implicit at both ends of the returned :class:`~core.model.solution.Route`.

Nearest neighbour is a heuristic, not a proof method.  Its report therefore
never carries a lower bound and never uses an optimality status.  If a budget
expires during construction, the remaining customers are appended in stable
index order.  That preserves a complete, independently checkable incumbent
without pretending that the greedy construction finished.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget

# A conservative accounting estimate for the list, set, and Python integer
# references used by the construction.  It is an algorithmic budget estimate,
# not a process RSS measurement (the immutable input instance is not charged).
_BYTES_PER_CUSTOMER = 96
_FALLBACK_BYTES_PER_CUSTOMER = 16


def _require_tsp(instance: Instance, solver_name: str) -> None:
    if instance.problem_type is not ProblemType.TSP:
        raise ValueError(
            f"{solver_name} solves TSP only; instance '{instance.name}' is "
            f"{instance.problem_type.value}"
        )


def nearest_neighbor_tour(
    instance: Instance,
    *,
    should_stop: Callable[[], bool] | None = None,
    max_steps: int | None = None,
) -> tuple[tuple[int, ...], int, bool]:
    """Return ``(tour, greedy_steps, completed_greedily)``.

    ``should_stop`` is checked before every greedy choice.  On interruption the
    still-unvisited nodes are appended in sorted order, so callers always get a
    complete feasible tour.  This utility performs no reporting; exact solvers
    use it only to obtain an initial incumbent.
    """

    _require_tsp(instance, "nearest neighbour")
    remaining = set(instance.customer_indices)
    tour: list[int] = []
    current = instance.depot_index
    steps = 0
    completed = True

    while remaining:
        if (max_steps is not None and steps >= max_steps) or (
            should_stop is not None and should_stop()
        ):
            completed = False
            tour.extend(sorted(remaining))
            break

        nxt = min(remaining, key=lambda node: (instance.matrix.cost(current, node), node))
        remaining.remove(nxt)
        tour.append(nxt)
        current = nxt
        steps += 1

    return tuple(tour), steps, completed


class NearestNeighborSolver:
    """Visit the closest unvisited customer until the tour is complete."""

    @property
    def name(self) -> str:
        return "nearest_neighbor"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        _require_tsp(instance, self.name)

        start = time.perf_counter()
        cpu_start = time.process_time()
        deadline = (
            start + budget.wall_time_ms / 1000.0
            if budget.wall_time_ms is not None
            else None
        )

        estimated_memory = len(instance.customer_indices) * _BYTES_PER_CUSTOMER
        memory_limit = (
            budget.max_memory_mb * 1024 * 1024
            if budget.max_memory_mb is not None
            else None
        )

        forced_reason: StopReason | None = None
        if memory_limit is not None and estimated_memory > memory_limit:
            # The stable input order is already materialised by Instance and is
            # a feasible zero-work fallback; do not allocate the greedy set.
            tour = instance.customer_indices
            steps = 0
            completed = False
            forced_reason = StopReason.MEMORY_CAP
        else:
            tour, steps, completed = nearest_neighbor_tour(
                instance,
                should_stop=(
                    (lambda: time.perf_counter() >= deadline)
                    if deadline is not None
                    else None
                ),
                max_steps=budget.max_nodes,
            )

        if forced_reason is not None:
            stop_reason = forced_reason
        elif completed:
            stop_reason = StopReason.COMPLETED
        elif budget.max_nodes is not None and steps >= budget.max_nodes:
            stop_reason = StopReason.NODE_CAP
        else:
            stop_reason = StopReason.TIMEOUT

        solution = Solution.single_tour(
            tour, vehicle_id=instance.vehicles[0].id
        )
        # This is deliberately independent of the construction logic.  A
        # heuristic result is not reportable merely because the heuristic says
        # it visited every node.
        check(instance, solution).raise_if_infeasible()
        objective = solution_cost(instance, solution)

        wall_ms = (time.perf_counter() - start) * 1000.0
        cpu_ms = (time.process_time() - cpu_start) * 1000.0
        peak_bytes = (
            64 + len(instance.customer_indices) * _FALLBACK_BYTES_PER_CUSTOMER
            if forced_reason is StopReason.MEMORY_CAP
            else estimated_memory
        )
        report = SolveReport(
            solver_name=self.name,
            problem_type=ProblemType.TSP,
            status=SolveStatus.HEURISTIC_FEASIBLE_TSP,
            stop_reason=stop_reason,
            objective_value=objective,
            objective_units=instance.matrix.unit,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            peak_memory_mb=peak_bytes / (1024 * 1024),
            nodes_created=steps,
            nodes_explored=steps,
            distance_matrix_hash=instance.matrix.content_hash,
            solver_config_hash=budget.config_hash(),
            extra={
                "construction_complete": str(completed).lower(),
                "tie_break": "node_index",
            },
        )
        return solution, report
