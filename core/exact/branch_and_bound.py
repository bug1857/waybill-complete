"""Budgeted best-first Branch & Bound for symmetric and asymmetric TSP.

The completion bound is the maximum of two independent relaxations:

* every still-required source must choose at least one outgoing edge; and
* every still-required destination must receive at least one incoming edge.

Both relaxations ignore degree matching and subtour constraints.  Ignoring
constraints can only make their minima cheaper than a real completion, so each
is a lower bound; the maximum of valid lower bounds is also valid.  The argument
does not require symmetry and therefore applies unchanged to directed road-cost
matrices.

Search is best-first.  That makes the minimum frontier key a global lower bound.
If a budget interrupts child generation, the expanded parent's bound is retained
as well: it covers every child not yet materialised and prevents a timeout from
silently losing its certificate.
"""

from __future__ import annotations

import heapq
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import count

from core.construct.nearest_neighbor import nearest_neighbor_tour
from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget

# Unlimited B&B above this point is almost certainly accidental.  Larger runs
# remain available when the caller states at least one finite resource budget.
MAX_UNBUDGETED_CUSTOMERS = 14
_BASE_STATE_BYTES = 384
_BYTES_PER_CUSTOMER_IN_STATE = 32
_BYTES_PER_CUSTOMER_IN_GREEDY_SEED = 96
_BYTES_PER_CUSTOMER_IN_INCUMBENT = 16


@dataclass(frozen=True, slots=True)
class _State:
    path: tuple[int, ...]
    remaining_mask: int
    last: int
    cost_so_far: int
    lower_bound: int


def _remaining_nodes(customers: tuple[int, ...], mask: int) -> list[int]:
    return [node for bit, node in enumerate(customers) if mask & (1 << bit)]


def _min_in_out_bound(
    instance: Instance,
    *,
    last: int,
    remaining_mask: int,
    cost_so_far: int,
    should_stop: Callable[[], bool] | None = None,
) -> int | None:
    """Admissible directed completion bound, or ``None`` if interrupted."""

    matrix = instance.matrix
    depot = instance.depot_index
    remaining = _remaining_nodes(instance.customer_indices, remaining_mask)
    if not remaining:
        return cost_so_far + matrix.cost(last, depot)

    if should_stop is not None and should_stop():
        return None

    # Outgoing relaxation: last must go to a remaining node.  Each remaining
    # node then goes to another remaining node or returns to the depot.
    outgoing = min(matrix.cost(last, node) for node in remaining)
    for source in remaining:
        if should_stop is not None and should_stop():
            return None
        outgoing += min(
            [matrix.cost(source, depot)]
            + [
                matrix.cost(source, target)
                for target in remaining
                if target != source
            ]
        )

    # Incoming relaxation: every remaining node receives an edge from the
    # current endpoint or another remaining node; the depot receives the final
    # edge from a remaining node.
    incoming = min(matrix.cost(source, depot) for source in remaining)
    possible_sources = [last, *remaining]
    for target in remaining:
        if should_stop is not None and should_stop():
            return None
        incoming += min(
            matrix.cost(source, target)
            for source in possible_sources
            if source != target
        )

    return cost_so_far + max(outgoing, incoming)


def completion_lower_bound(
    instance: Instance, partial_tour: Sequence[int] = ()
) -> int:
    """Return an admissible bound for all tours extending ``partial_tour``.

    ``partial_tour`` contains customer indices only; the depot is implicit at
    the start.  This public function exists so the most important B&B invariant
    -- lower bound no greater than the brute-force optimum -- can be tested
    independently of the search.
    """

    if instance.problem_type is not ProblemType.TSP:
        raise ValueError(
            f"completion bound is for TSP only; instance '{instance.name}' is "
            f"{instance.problem_type.value}"
        )
    partial = tuple(partial_tour)
    if len(set(partial)) != len(partial):
        raise ValueError("partial_tour contains a duplicate customer")
    customers = instance.customer_indices
    customer_set = set(customers)
    if any(node not in customer_set for node in partial):
        raise ValueError("partial_tour must contain customer indices only")

    matrix = instance.matrix
    last = instance.depot_index
    cost_so_far = 0
    for node in partial:
        cost_so_far += matrix.cost(last, node)
        last = node
    visited = set(partial)
    remaining_mask = 0
    for bit, node in enumerate(customers):
        if node not in visited:
            remaining_mask |= 1 << bit
    result = _min_in_out_bound(
        instance,
        last=last,
        remaining_mask=remaining_mask,
        cost_so_far=cost_so_far,
    )
    assert result is not None
    return result


class BranchAndBoundSolver:
    """Best-first exact search with an admissible min-in/out bound."""

    def __init__(
        self, max_unbudgeted_customers: int = MAX_UNBUDGETED_CUSTOMERS
    ) -> None:
        if max_unbudgeted_customers < 0:
            raise ValueError("max_unbudgeted_customers must be non-negative")
        self._max_unbudgeted_customers = max_unbudgeted_customers

    @property
    def name(self) -> str:
        return "branch_and_bound_min_in_out"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        if instance.problem_type is not ProblemType.TSP:
            raise ValueError(
                f"Branch & Bound solves TSP only; instance '{instance.name}' is "
                f"{instance.problem_type.value}"
            )

        customers = instance.customer_indices
        customer_count = len(customers)
        if budget.is_unlimited and customer_count > self._max_unbudgeted_customers:
            raise ValueError(
                f"unbudgeted Branch & Bound is limited to "
                f"{self._max_unbudgeted_customers} customers; instance "
                f"'{instance.name}' has {customer_count}. Supply a wall-time, "
                "node, or memory budget for a larger exploratory run."
            )

        start = time.perf_counter()
        cpu_start = time.process_time()
        deadline = (
            start + budget.wall_time_ms / 1000.0
            if budget.wall_time_ms is not None
            else None
        )
        timed_out = (
            (lambda: time.perf_counter() >= deadline)
            if deadline is not None
            else None
        )

        state_bytes = (
            _BASE_STATE_BYTES + _BYTES_PER_CUSTOMER_IN_STATE * customer_count
        )
        incumbent_bytes = 64 + _BYTES_PER_CUSTOMER_IN_INCUMBENT * customer_count
        greedy_seed_bytes = (
            _BYTES_PER_CUSTOMER_IN_GREEDY_SEED * customer_count
        )
        memory_limit = (
            budget.max_memory_mb * 1024 * 1024
            if budget.max_memory_mb is not None
            else None
        )
        if memory_limit is not None and greedy_seed_bytes > memory_limit:
            # The instance already exposes this immutable tuple.  Reusing it as
            # the incumbent avoids allocating the nearest-neighbour set when a
            # deliberately tiny memory budget cannot accommodate that seed.
            incumbent_tour = customers
            seed_peak_bytes = incumbent_bytes
            incumbent_seed = "input_order_memory_fallback"
        else:
            incumbent_tour, _, greedy_completed = nearest_neighbor_tour(
                instance, should_stop=timed_out
            )
            seed_peak_bytes = max(greedy_seed_bytes, incumbent_bytes)
            incumbent_seed = (
                "nearest_neighbor"
                if greedy_completed
                else "nearest_neighbor_then_input_order_on_timeout"
            )
        incumbent_solution = Solution.single_tour(
            incumbent_tour, vehicle_id=instance.vehicles[0].id
        )
        check(instance, incumbent_solution).raise_if_infeasible()
        incumbent_cost = solution_cost(instance, incumbent_solution)

        if customer_count == 0:
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent_solution,
                optimal=True,
                stop_reason=StopReason.OPTIMAL,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes_created=0,
                nodes_explored=0,
                nodes_pruned=0,
                peak_frontier=0,
                peak_bytes=0,
                bound_time_ms=0.0,
                incumbent_seed=incumbent_seed,
            )

        if (
            memory_limit is not None
            and incumbent_bytes + state_bytes > memory_limit
        ):
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent_solution,
                optimal=False,
                stop_reason=StopReason.MEMORY_CAP,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes_created=0,
                nodes_explored=0,
                nodes_pruned=0,
                peak_frontier=0,
                peak_bytes=seed_peak_bytes,
                bound_time_ms=0.0,
                incumbent_seed=incumbent_seed,
            )

        if timed_out is not None and timed_out():
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent_solution,
                optimal=False,
                stop_reason=StopReason.TIMEOUT,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes_created=0,
                nodes_explored=0,
                nodes_pruned=0,
                peak_frontier=0,
                peak_bytes=seed_peak_bytes,
                bound_time_ms=0.0,
                incumbent_seed=incumbent_seed,
            )

        bound_start = time.perf_counter()
        root_bound = _min_in_out_bound(
            instance,
            last=instance.depot_index,
            remaining_mask=(1 << customer_count) - 1,
            cost_so_far=0,
            should_stop=timed_out,
        )
        bound_time_ms = (time.perf_counter() - bound_start) * 1000.0
        if root_bound is None:
            return self._finish(
                instance=instance,
                budget=budget,
                solution=incumbent_solution,
                optimal=False,
                stop_reason=StopReason.TIMEOUT,
                lower_bound=0,
                start=start,
                cpu_start=cpu_start,
                nodes_created=0,
                nodes_explored=0,
                nodes_pruned=0,
                peak_frontier=0,
                peak_bytes=seed_peak_bytes,
                bound_time_ms=bound_time_ms,
                incumbent_seed=incumbent_seed,
            )

        root = _State(
            path=(),
            remaining_mask=(1 << customer_count) - 1,
            last=instance.depot_index,
            cost_so_far=0,
            lower_bound=root_bound,
        )
        serial = count()
        frontier: list[tuple[int, int, int, _State]] = [
            (root.lower_bound, 0, next(serial), root)
        ]
        nodes_created = 1
        nodes_explored = 0
        nodes_pruned = 0
        peak_frontier = 1
        peak_bytes = max(seed_peak_bytes, incumbent_bytes + state_bytes)
        stop_reason: StopReason | None = None
        active_lower_bound: int | None = None
        matrix = instance.matrix

        while frontier:
            # If the cheapest live subtree cannot beat the incumbent, the
            # incumbent is proven and no budget check can undo that fact.
            if frontier[0][0] >= incumbent_cost:
                nodes_pruned += len(frontier)
                frontier.clear()
                break

            if budget.max_nodes is not None and nodes_explored >= budget.max_nodes:
                stop_reason = StopReason.NODE_CAP
                break
            if timed_out is not None and timed_out():
                stop_reason = StopReason.TIMEOUT
                break

            _, _, _, state = heapq.heappop(frontier)
            nodes_explored += 1
            if state.lower_bound >= incumbent_cost:
                nodes_pruned += 1
                continue

            active_lower_bound = state.lower_bound
            completed_expansion = True
            candidate_bits = [
                bit
                for bit in range(customer_count)
                if state.remaining_mask & (1 << bit)
            ]
            candidate_bits.sort(
                key=lambda bit: (matrix.cost(state.last, customers[bit]), customers[bit])
            )

            for bit in candidate_bits:
                if timed_out is not None and timed_out():
                    stop_reason = StopReason.TIMEOUT
                    completed_expansion = False
                    break

                node = customers[bit]
                remaining_mask = state.remaining_mask ^ (1 << bit)
                cost_so_far = state.cost_so_far + matrix.cost(state.last, node)
                path = (*state.path, node)
                nodes_created += 1

                if remaining_mask == 0:
                    tour_cost = cost_so_far + matrix.cost(node, instance.depot_index)
                    if tour_cost < incumbent_cost:
                        incumbent_cost = tour_cost
                        incumbent_solution = Solution.single_tour(
                            path, vehicle_id=instance.vehicles[0].id
                        )
                    continue

                bound_start = time.perf_counter()
                child_bound = _min_in_out_bound(
                    instance,
                    last=node,
                    remaining_mask=remaining_mask,
                    cost_so_far=cost_so_far,
                    should_stop=timed_out,
                )
                bound_time_ms += (time.perf_counter() - bound_start) * 1000.0
                if child_bound is None:
                    stop_reason = StopReason.TIMEOUT
                    completed_expansion = False
                    break

                if child_bound >= incumbent_cost:
                    nodes_pruned += 1
                    continue

                if (
                    memory_limit is not None
                    # The expanded parent remains live until all children are
                    # generated, so account for both it and the prospective
                    # child in addition to the existing frontier.
                    and incumbent_bytes
                    + (len(frontier) + 2) * state_bytes
                    > memory_limit
                ):
                    stop_reason = StopReason.MEMORY_CAP
                    completed_expansion = False
                    break

                child = _State(
                    path=path,
                    remaining_mask=remaining_mask,
                    last=node,
                    cost_so_far=cost_so_far,
                    lower_bound=child_bound,
                )
                heapq.heappush(
                    frontier,
                    (child_bound, -len(path), next(serial), child),
                )
                peak_frontier = max(peak_frontier, len(frontier))
                peak_bytes = max(
                    peak_bytes,
                    incumbent_bytes + (len(frontier) + 1) * state_bytes,
                )

            if completed_expansion:
                active_lower_bound = None
            if stop_reason is not None:
                break

        remaining_bounds = [frontier[0][0]] if frontier else []
        if active_lower_bound is not None:
            remaining_bounds.append(active_lower_bound)

        if not remaining_bounds:
            optimal = True
            global_lower_bound = incumbent_cost
            stop_reason = StopReason.OPTIMAL
        else:
            global_lower_bound = min(remaining_bounds)
            # An incumbent improvement during a partially completed expansion
            # can make every retained bound meet it.  That is already a proof.
            if global_lower_bound >= incumbent_cost:
                optimal = True
                global_lower_bound = incumbent_cost
                stop_reason = StopReason.OPTIMAL
            else:
                optimal = False
                assert stop_reason is not None

        check(instance, incumbent_solution).raise_if_infeasible()
        rescored = solution_cost(instance, incumbent_solution)
        if rescored != incumbent_cost:
            raise RuntimeError(
                f"B&B incumbent cost {incumbent_cost} != reconstructed cost {rescored}"
            )

        return self._finish(
            instance=instance,
            budget=budget,
            solution=incumbent_solution,
            optimal=optimal,
            stop_reason=stop_reason,
            lower_bound=global_lower_bound,
            start=start,
            cpu_start=cpu_start,
            nodes_created=nodes_created,
            nodes_explored=nodes_explored,
            nodes_pruned=nodes_pruned,
            peak_frontier=peak_frontier,
            peak_bytes=peak_bytes,
            bound_time_ms=bound_time_ms,
            incumbent_seed=incumbent_seed,
        )

    def _finish(
        self,
        *,
        instance: Instance,
        budget: Budget,
        solution: Solution,
        optimal: bool,
        stop_reason: StopReason,
        lower_bound: int,
        start: float,
        cpu_start: float,
        nodes_created: int,
        nodes_explored: int,
        nodes_pruned: int,
        peak_frontier: int,
        peak_bytes: int,
        bound_time_ms: float,
        incumbent_seed: str,
    ) -> tuple[Solution, SolveReport]:
        check(instance, solution).raise_if_infeasible()
        objective = solution_cost(instance, solution)
        # A feasible incumbent meeting a valid global lower bound is already a
        # certificate.  Do not label that run as interrupted merely because a
        # resource guard was also reached.
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
            nodes_created=nodes_created,
            nodes_explored=nodes_explored,
            nodes_pruned=nodes_pruned,
            peak_frontier=peak_frontier,
            bound_time_ms=bound_time_ms,
            distance_matrix_hash=instance.matrix.content_hash,
            solver_config_hash=budget.config_hash(),
            extra={
                "bound": "min_in_out",
                "search_strategy": "best_first",
                "incumbent_seed": incumbent_seed,
                "node_budget_counter": "nodes_explored",
                "state_bytes_estimate": str(
                    _BASE_STATE_BYTES
                    + _BYTES_PER_CUSTOMER_IN_STATE
                    * len(instance.customer_indices)
                ),
            },
        )
        return solution, report
