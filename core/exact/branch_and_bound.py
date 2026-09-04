"""Branch & Bound over partial tours.

Depth-first search from the depot, extending one stop at a time. At each node
the cost so far plus a lower bound on completing the tour is compared against
the incumbent; if it cannot beat the incumbent, the whole subtree is discarded
without being built.

Two decisions shape how well it works, and both are measured rather than assumed:

**The incumbent seed.** Starting from a greedy tour rather than from infinity
means pruning begins at the first node instead of after the first full descent.

**Depth-first, not best-first.** DFS holds one path in memory, so the frontier
cannot explode; best-first explores fewer nodes but its queue grows without
bound. Phase 3 compares them and records peak frontier for each, which turns a
memory blow-up into a curve rather than a crash.

Instrumentation is deliberately thorough: nodes created, explored, and pruned,
peak depth, and bound computation time recorded separately from search time. A
tighter bound that costs too much per node can lose overall, and that trade is
invisible unless the two costs are timed apart.
"""

import time

from core.exact.bounds.reduction import completion_bound
from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget


class BranchAndBoundSolver:
    """Exact TSP by depth-first Branch & Bound with a reduced-cost bound."""

    def __init__(self, bound=completion_bound, bound_name: str = "reduced_cost") -> None:
        self._bound = bound
        self._bound_name = bound_name

    @property
    def name(self) -> str:
        return f"branch_and_bound[{self._bound_name}]"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        if instance.problem_type is not ProblemType.TSP:
            raise ValueError(
                f"Branch & Bound solves TSP only; '{instance.name}' is "
                f"{instance.problem_type.value}"
            )

        matrix = instance.matrix
        depot = instance.depot_index
        customers = list(instance.customer_indices)

        start_wall = time.perf_counter()
        start_cpu = time.process_time()
        deadline = (
            start_wall + budget.wall_time_ms / 1000.0
            if budget.wall_time_ms is not None
            else None
        )

        if not customers:
            return Solution.single_tour((), instance.vehicles[0].id), self._report(
                instance, 0, 0, StopReason.OPTIMAL, 0, 0, 0, 0, 0.0, 0.0, 0.0, budget
            )

        # Seed the incumbent so pruning can start at the root.
        from core.construct.nearest_neighbour import NearestNeighbourSolver

        seed_solution, seed_report = NearestNeighbourSolver().solve(instance)
        best_cost = seed_report.objective_value
        best_sequence = tuple(seed_solution.routes[0].sequence)

        created = explored = pruned = 0
        peak_depth = 0
        bound_ms = 0.0
        timed_out = False

        unvisited = set(customers)
        path: list[int] = []

        def descend(last: int, cost_so_far: int) -> None:
            nonlocal best_cost, best_sequence, created, explored, pruned
            nonlocal peak_depth, bound_ms, timed_out

            if timed_out:
                return
            if deadline is not None and time.perf_counter() > deadline:
                timed_out = True
                return

            explored += 1
            peak_depth = max(peak_depth, len(path))

            if not unvisited:
                total = cost_so_far + matrix.cost(last, depot)
                if total < best_cost:
                    best_cost = total
                    best_sequence = tuple(path)
                return

            for node in sorted(unvisited, key=lambda c: matrix.cost(last, c)):
                created += 1
                step = cost_so_far + matrix.cost(last, node)
                if step >= best_cost:
                    pruned += 1
                    continue

                unvisited.discard(node)
                path.append(node)

                t0 = time.perf_counter()
                lb = step + self._bound(matrix, node, unvisited, depot)
                bound_ms += (time.perf_counter() - t0) * 1000.0

                if lb < best_cost:
                    descend(node, step)
                else:
                    pruned += 1

                path.pop()
                unvisited.add(node)

        descend(depot, 0)

        wall_ms = (time.perf_counter() - start_wall) * 1000.0
        cpu_ms = (time.process_time() - start_cpu) * 1000.0

        solution = Solution.single_tour(best_sequence, instance.vehicles[0].id)
        stop_reason = StopReason.TIMEOUT if timed_out else StopReason.OPTIMAL

        return solution, self._report(
            instance,
            best_cost,
            best_cost if not timed_out else 0,
            stop_reason,
            created,
            explored,
            pruned,
            peak_depth,
            wall_ms,
            cpu_ms,
            bound_ms,
            budget,
        )

    def _report(
        self, instance, cost, lower_bound, stop_reason, created, explored,
        pruned, peak_depth, wall_ms, cpu_ms, bound_ms, budget,
    ) -> SolveReport:
        proven = stop_reason is StopReason.OPTIMAL
        return SolveReport(
            solver_name=self.name,
            problem_type=ProblemType.TSP,
            status=(
                SolveStatus.PROVEN_OPTIMAL_TSP
                if proven
                else SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
            ),
            stop_reason=stop_reason,
            objective_value=cost,
            objective_units=instance.matrix.unit,
            # A completed search proves its own answer optimal. A timed-out one
            # reports the weakest defensible bound rather than none, so the
            # residual gap is still expressible.
            best_lower_bound=cost if proven else lower_bound,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            nodes_created=created,
            nodes_explored=explored,
            nodes_pruned=pruned,
            peak_frontier=peak_depth,
            bound_time_ms=bound_ms,
            distance_matrix_hash=instance.matrix.content_hash,
            solver_config_hash=budget.config_hash(),
            extra={"bound": self._bound_name, "search": "dfs"},
        )
