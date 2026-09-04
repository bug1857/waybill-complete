"""Clarke-Wright savings.

The one classical constructive heuristic that is natively a *fleet* algorithm.
It answers the partitioning question and the sequencing question in a single
pass, which is why dispatch systems ran on it for decades.

Start with one dedicated out-and-back route per customer. For every pair,
compute the saving from serving them on one route instead of two::

    s(i, j) = d(depot, i) + d(depot, j) - d(i, j)

Merge greedily in descending order of saving, skipping any merge that would
breach capacity or join two customers that are not both at the end of their
routes. What remains is a set of routes.

On a single-vehicle unlimited-capacity instance this collapses to a TSP
construction, which is what makes it directly comparable to nearest neighbour.
"""

import time

from core.model.instance import Instance, ProblemType
from core.model.solution import Route, Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget


class ClarkeWrightSolver:
    """Savings-based construction, capacity aware."""

    @property
    def name(self) -> str:
        return "clarke_wright"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        matrix = instance.matrix
        depot = instance.depot_index
        customers = list(instance.customer_indices)

        start_wall = time.perf_counter()
        start_cpu = time.process_time()

        # One route per customer to begin with.
        routes: dict[int, list[int]] = {c: [c] for c in customers}
        route_of: dict[int, int] = {c: c for c in customers}
        load: dict[int, int] = {c: instance.stops[c].demand for c in customers}

        capacity = max((v.capacity for v in instance.vehicles), default=0)
        max_routes = len(instance.vehicles)

        savings = [
            (
                matrix.cost(depot, i) + matrix.cost(depot, j) - matrix.cost(i, j),
                i,
                j,
            )
            for idx, i in enumerate(customers)
            for j in customers[idx + 1 :]
        ]
        savings.sort(key=lambda t: t[0], reverse=True)

        merges = 0
        for saving, i, j in savings:
            if saving <= 0:
                break
            ri, rj = route_of[i], route_of[j]
            if ri == rj:
                continue
            a, b = routes[ri], routes[rj]
            # Only endpoints may be joined; interior customers already have two
            # neighbours and cannot take another.
            if not ((a[0] == i or a[-1] == i) and (b[0] == j or b[-1] == j)):
                continue
            if load[ri] + load[rj] > capacity:
                continue

            if a[-1] != i:
                a.reverse()
            if b[0] != j:
                b.reverse()

            merged = a + b
            routes[ri] = merged
            load[ri] += load[rj]
            for node in b:
                route_of[node] = ri
            del routes[rj]
            del load[rj]
            merges += 1

        wall_ms = (time.perf_counter() - start_wall) * 1000.0
        cpu_ms = (time.process_time() - start_cpu) * 1000.0

        ordered = list(routes.values())
        vehicles = instance.vehicles
        built = tuple(
            Route(vehicle_id=vehicles[idx % len(vehicles)].id, sequence=tuple(seq))
            for idx, seq in enumerate(ordered)
        )
        solution = Solution(routes=built)

        from core.eval.objective import solution_cost

        over_fleet = len(ordered) > max_routes
        report = SolveReport(
            solver_name=self.name,
            problem_type=instance.problem_type,
            status=(
                SolveStatus.HEURISTIC_INFEASIBLE
                if over_fleet
                else SolveStatus.HEURISTIC_FEASIBLE_CVRPTW
                if instance.problem_type is not ProblemType.TSP
                else SolveStatus.REFERENCE_GAP_ONLY
            ),
            stop_reason=StopReason.COMPLETED,
            objective_value=solution_cost(instance, solution),
            objective_units=matrix.unit,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            nodes_explored=merges,
            distance_matrix_hash=matrix.content_hash,
            solver_config_hash=budget.config_hash(),
            extra={"routes_built": str(len(ordered)), "merges": str(merges)},
        )
        return solution, report
