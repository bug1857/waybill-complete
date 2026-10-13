"""Exact Held--Karp dynamic programming for TSP.

The depot is fixed and a state ``(S, j)`` stores the cheapest path from the
depot that visits exactly customer subset ``S`` and ends at customer ``j``.
There are ``m * 2**(m-1)`` such states for ``m`` customers, which is why this
solver has an explicit size guard and a conservative memory preflight instead
of implying that dynamic programming scales to medium-sized routing problems.

If a budget is reached, a complete nearest-neighbour incumbent is returned with
a trivial but valid lower bound of zero.  Partial DP layers do not constitute an
optimality certificate, so a limited run never claims proof.
"""

from __future__ import annotations

import time
from itertools import combinations

from core.construct.nearest_neighbor import nearest_neighbor_tour
from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget

# The Python implementation stores a tuple key and integer value in each of two
# dictionaries (cost and parent).  This estimate is deliberately conservative;
# it exists to make a memory budget enforceable before a catastrophic allocation.
ESTIMATED_BYTES_PER_STATE = 320
ESTIMATED_BYTES_PER_GREEDY_CUSTOMER = 96
ESTIMATED_BYTES_PER_INCUMBENT_CUSTOMER = 16
MAX_SUPPORTED_CUSTOMERS = 18


def projected_state_count(customer_count: int) -> int:
    """Number of Held--Karp states for ``customer_count`` non-depot nodes."""

    if customer_count < 0:
        raise ValueError("customer_count must be non-negative")
    if customer_count == 0:
        return 0
    return customer_count * (1 << (customer_count - 1))


class HeldKarpSolver:
    """Solve a small TSP exactly using subset dynamic programming."""

    def __init__(self, max_customers: int = MAX_SUPPORTED_CUSTOMERS) -> None:
        if max_customers < 0:
            raise ValueError("max_customers must be non-negative")
        self._max_customers = max_customers

    @property
    def name(self) -> str:
        return "held_karp"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        if instance.problem_type is not ProblemType.TSP:
            raise ValueError(
                f"Held--Karp solves TSP only; instance '{instance.name}' is "
                f"{instance.problem_type.value}"
            )

        customers = instance.customer_indices
        customer_count = len(customers)
        if customer_count > self._max_customers:
            raise ValueError(
                f"instance '{instance.name}' has {customer_count} customers, above "
                f"the Held--Karp limit of {self._max_customers}; its state table "
                f"would contain {projected_state_count(customer_count):,} entries"
            )

        start = time.perf_counter()
        cpu_start = time.process_time()
        deadline = (
            start + budget.wall_time_ms / 1000.0
            if budget.wall_time_ms is not None
            else None
        )

        # Always preserve a complete incumbent.  The construction observes the
        # same wall-clock deadline and falls back to stable customer order if it
        # expires midway.
        incumbent_tour, _, _ = nearest_neighbor_tour(
            instance,
            should_stop=(
                (lambda: time.perf_counter() >= deadline)
                if deadline is not None
                else None
            ),
        )
        incumbent = Solution.single_tour(
            incumbent_tour, vehicle_id=instance.vehicles[0].id
        )
        check(instance, incumbent).raise_if_infeasible()
        incumbent_cost = solution_cost(instance, incumbent)

        projected_states = projected_state_count(customer_count)
        seed_peak_bytes = (
            customer_count * ESTIMATED_BYTES_PER_GREEDY_CUSTOMER
        )
        incumbent_bytes = (
            64 + customer_count * ESTIMATED_BYTES_PER_INCUMBENT_CUSTOMER
        )
        projected_bytes = (
            projected_states * ESTIMATED_BYTES_PER_STATE + incumbent_bytes
        )
        memory_limit = (
            budget.max_memory_mb * 1024 * 1024
            if budget.max_memory_mb is not None
            else None
        )

        if customer_count == 0:
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent,
                objective=0,
                optimal=True,
                stop_reason=StopReason.OPTIMAL,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes=0,
                peak_bytes=seed_peak_bytes,
                projected_states=0,
            )

        if memory_limit is not None and projected_bytes > memory_limit:
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent,
                objective=incumbent_cost,
                optimal=False,
                stop_reason=StopReason.MEMORY_CAP,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes=0,
                peak_bytes=seed_peak_bytes,
                projected_states=projected_states,
            )

        if deadline is not None and time.perf_counter() >= deadline:
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent,
                objective=incumbent_cost,
                optimal=False,
                stop_reason=StopReason.TIMEOUT,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes=0,
                peak_bytes=seed_peak_bytes,
                projected_states=projected_states,
            )

        matrix = instance.matrix
        depot = instance.depot_index
        costs: dict[tuple[int, int], int] = {}
        parents: dict[tuple[int, int], int] = {}
        nodes = 0
        peak_bytes = seed_peak_bytes
        stop_reason: StopReason | None = None

        def budget_reason(next_state_count: int) -> StopReason | None:
            if budget.max_nodes is not None and nodes >= budget.max_nodes:
                return StopReason.NODE_CAP
            if deadline is not None and time.perf_counter() >= deadline:
                return StopReason.TIMEOUT
            if (
                memory_limit is not None
                and next_state_count * ESTIMATED_BYTES_PER_STATE > memory_limit
            ):
                return StopReason.MEMORY_CAP
            return None

        # Base states: depot -> j.
        for local_j, node_j in enumerate(customers):
            stop_reason = budget_reason(nodes + 1)
            if stop_reason is not None:
                break
            key = (1 << local_j, local_j)
            costs[key] = matrix.cost(depot, node_j)
            parents[key] = -1
            nodes += 1
            peak_bytes = max(
                peak_bytes,
                incumbent_bytes + nodes * ESTIMATED_BYTES_PER_STATE,
            )

        # Build larger subsets.  The periodic deadline check inside the
        # predecessor loop prevents one expensive state from running far past a
        # very small wall-clock budget.
        if stop_reason is None:
            for subset_size in range(2, customer_count + 1):
                for subset in combinations(range(customer_count), subset_size):
                    mask = 0
                    for bit in subset:
                        mask |= 1 << bit
                    for local_j in subset:
                        stop_reason = budget_reason(nodes + 1)
                        if stop_reason is not None:
                            break

                        previous_mask = mask ^ (1 << local_j)
                        best_cost: int | None = None
                        best_previous = -1
                        for local_k in subset:
                            if local_k == local_j:
                                continue
                            if deadline is not None and time.perf_counter() >= deadline:
                                stop_reason = StopReason.TIMEOUT
                                break
                            candidate = costs[(previous_mask, local_k)] + matrix.cost(
                                customers[local_k], customers[local_j]
                            )
                            if best_cost is None or candidate < best_cost:
                                best_cost = candidate
                                best_previous = local_k
                        if stop_reason is not None:
                            break

                        # subset_size >= 2 guarantees a predecessor.
                        assert best_cost is not None and best_previous >= 0
                        costs[(mask, local_j)] = best_cost
                        parents[(mask, local_j)] = best_previous
                        nodes += 1
                        peak_bytes = max(
                            peak_bytes,
                            incumbent_bytes + nodes * ESTIMATED_BYTES_PER_STATE,
                        )
                    if stop_reason is not None:
                        break
                if stop_reason is not None:
                    break

        if stop_reason is not None:
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent,
                objective=incumbent_cost,
                optimal=False,
                stop_reason=stop_reason,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes=nodes,
                peak_bytes=peak_bytes,
                projected_states=projected_states,
            )

        full_mask = (1 << customer_count) - 1
        last = min(
            range(customer_count),
            key=lambda local_j: costs[(full_mask, local_j)]
            + matrix.cost(customers[local_j], depot),
        )
        optimum = costs[(full_mask, last)] + matrix.cost(customers[last], depot)

        reverse_tour: list[int] = []
        mask = full_mask
        while last >= 0:
            reverse_tour.append(customers[last])
            previous = parents[(mask, last)]
            mask ^= 1 << last
            last = previous
        optimal_tour = tuple(reversed(reverse_tour))
        solution = Solution.single_tour(
            optimal_tour, vehicle_id=instance.vehicles[0].id
        )
        check(instance, solution).raise_if_infeasible()
        # Re-score through the shared objective rather than trusting the DP
        # accumulator at the reporting boundary.
        objective = solution_cost(instance, solution)
        if objective != optimum:
            raise RuntimeError(
                f"Held--Karp reconstruction cost {objective} != DP optimum {optimum}"
            )

        return self._finish(
            instance=instance,
            budget=budget,
            solution=solution,
            objective=objective,
            optimal=True,
            stop_reason=StopReason.OPTIMAL,
            lower_bound=objective,
            start=start,
            cpu_start=cpu_start,
            nodes=nodes,
            peak_bytes=peak_bytes,
            projected_states=projected_states,
        )

    def _finish(
        self,
        *,
        instance: Instance,
        budget: Budget,
        solution: Solution,
        objective: int,
        optimal: bool,
        stop_reason: StopReason,
        lower_bound: int,
        start: float,
        cpu_start: float,
        nodes: int,
        peak_bytes: int,
        projected_states: int,
    ) -> tuple[Solution, SolveReport]:
        # Equality of a valid lower bound and a feasible incumbent is itself a
        # proof, even if the resource check that discovered it was otherwise an
        # interruption (notably a zero-cost instance with the universal LB 0).
        if not optimal and lower_bound == objective:
            optimal = True
            stop_reason = StopReason.OPTIMAL
        report = SolveReport(
            solver_name=self.name,
            problem_type=ProblemType.TSP,
            status=(
                SolveStatus.PROVEN_OPTIMAL_TSP
                if optimal
                else SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT
            ),
            stop_reason=stop_reason,
            objective_value=objective,
            objective_units=instance.matrix.unit,
            best_lower_bound=lower_bound,
            wall_time_ms=(time.perf_counter() - start) * 1000.0,
            cpu_time_ms=(time.process_time() - cpu_start) * 1000.0,
            peak_memory_mb=peak_bytes / (1024 * 1024),
            nodes_created=nodes,
            nodes_explored=nodes,
            # DP has a table, not a search frontier.  Reusing this B&B-specific
            # field would make cross-solver instrumentation misleading.
            peak_frontier=0,
            distance_matrix_hash=instance.matrix.content_hash,
            solver_config_hash=budget.config_hash(),
            extra={
                "projected_states": str(projected_states),
                "state_bytes_estimate": str(ESTIMATED_BYTES_PER_STATE),
                "greedy_customer_bytes_estimate": str(
                    ESTIMATED_BYTES_PER_GREEDY_CUSTOMER
                ),
                "max_customers": str(self._max_customers),
                "states_materialized": str(nodes),
                "node_budget_counter": "dp_states_materialized",
            },
        )
        return solution, report
