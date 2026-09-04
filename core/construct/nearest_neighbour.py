"""Nearest neighbour construction.

The assignment's "Greedy": from the current stop, always go to the nearest one
not yet visited. O(n^2), instant, and the baseline every other method is
measured against.

Its weakness is structural rather than incidental. Because it never looks ahead,
the stops it skips early become isolated, and the final legs of the tour are
long returns across ground already covered. The size of that penalty is one of
the numbers this project exists to measure, so it is not asserted here.
"""

import time

from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget


class NearestNeighbourSolver:
    """Greedy nearest-unvisited construction from the depot."""

    def __init__(self, start: int | None = None) -> None:
        self._start = start

    @property
    def name(self) -> str:
        return "nearest_neighbour"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        matrix = instance.matrix
        depot = instance.depot_index
        remaining = set(instance.customer_indices)

        start_wall = time.perf_counter()
        start_cpu = time.process_time()

        sequence: list[int] = []
        current = self._start if self._start is not None else depot
        if current != depot and current in remaining:
            remaining.discard(current)
            sequence.append(current)

        steps = 0
        while remaining:
            steps += 1
            nearest = min(remaining, key=lambda node: matrix.cost(current, node))
            remaining.discard(nearest)
            sequence.append(nearest)
            current = nearest

        wall_ms = (time.perf_counter() - start_wall) * 1000.0
        cpu_ms = (time.process_time() - start_cpu) * 1000.0

        solution = Solution.single_tour(
            tuple(sequence), vehicle_id=instance.vehicles[0].id
        )
        from core.eval.objective import solution_cost

        report = SolveReport(
            solver_name=self.name,
            problem_type=instance.problem_type,
            status=(
                SolveStatus.HEURISTIC_FEASIBLE_CVRPTW
                if instance.problem_type is not ProblemType.TSP
                else SolveStatus.REFERENCE_GAP_ONLY
            ),
            stop_reason=StopReason.COMPLETED,
            objective_value=solution_cost(instance, solution),
            objective_units=matrix.unit,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            nodes_explored=steps,
            distance_matrix_hash=matrix.content_hash,
            solver_config_hash=budget.config_hash(),
        )
        return solution, report
