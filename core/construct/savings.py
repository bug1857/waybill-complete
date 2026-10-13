"""Directed Clarke-Wright savings construction for fixed-fleet CVRPTW.

The construction starts with one route per customer and joins a route tail to a
different route head in descending directed-savings order. Ordered pairs are
used deliberately: on road matrices, joining ``i -> j`` need not save the same
amount as ``j -> i``. Every proposed route is checked against at least one real
vehicle before it is accepted, and the final fleet plan is independently
validated before it receives feasible wording.
"""

import time
from dataclasses import dataclass

from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance, ProblemType
from core.model.solution import Route, Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget

_ESTIMATED_BYTES_PER_SAVING = 72


@dataclass(frozen=True, slots=True)
class SavingsStats:
    savings_pairs: int
    pairs_evaluated: int
    merges_accepted: int
    positive_merges: int
    initial_routes: int
    final_routes: int


def _route_fits_vehicle(
    instance: Instance,
    sequence: tuple[int, ...],
    vehicle,
) -> bool:
    load = sum(instance.stops[node].demand for node in sequence)
    if load > vehicle.capacity:
        return False
    if not instance.has_time_constraints or not sequence:
        return True

    t = vehicle.shift_start
    previous = instance.depot_index
    for node in sequence:
        t += instance.travel_time(previous, node)
        window = instance.stops[node].time_window
        t = max(t, window.earliest)
        if t > window.latest:
            return False
        t += instance.stops[node].service_time
        previous = node
    t += instance.travel_time(previous, instance.depot_index)
    if t > vehicle.shift_end:
        return False
    if (
        vehicle.max_route_duration is not None
        and t - vehicle.shift_start > vehicle.max_route_duration
    ):
        return False
    return True


def _compatible_vehicle_ids(
    instance: Instance,
    sequence: tuple[int, ...],
) -> tuple[int, ...]:
    return tuple(
        vehicle.id
        for vehicle in instance.vehicles
        if _route_fits_vehicle(instance, sequence, vehicle)
    )


def _assign_all_routes(
    instance: Instance,
    sequences: tuple[tuple[int, ...], ...],
) -> Solution | None:
    """Find a deterministic one-route-per-vehicle assignment by backtracking."""
    if len(sequences) > len(instance.vehicles):
        return None

    options = tuple(
        _compatible_vehicle_ids(instance, sequence) for sequence in sequences
    )
    if any(not vehicle_ids for vehicle_ids in options):
        return None

    order = sorted(
        range(len(sequences)),
        key=lambda index: (
            len(options[index]),
            -len(sequences[index]),
            sequences[index],
        ),
    )
    assignment: dict[int, int] = {}

    def visit(position: int, used: frozenset[int]) -> bool:
        if position == len(order):
            return True
        route_index = order[position]
        for vehicle_id in options[route_index]:
            if vehicle_id in used:
                continue
            assignment[route_index] = vehicle_id
            if visit(position + 1, used | {vehicle_id}):
                return True
            del assignment[route_index]
        return False

    if not visit(0, frozenset()):
        return None
    routes = tuple(
        sorted(
            (
                Route(assignment[index], sequence)
                for index, sequence in enumerate(sequences)
            ),
            key=lambda route: route.vehicle_id,
        )
    )
    return Solution(routes)


def _partial_solution(
    instance: Instance,
    sequences: tuple[tuple[int, ...], ...],
) -> Solution:
    """Preserve a maximal deterministic diagnostic incumbent."""
    used: set[int] = set()
    assigned: list[Route] = []
    served: set[int] = set()
    for sequence in sorted(sequences, key=lambda route: (-len(route), route)):
        compatible = _compatible_vehicle_ids(instance, sequence)
        vehicle_id = next((item for item in compatible if item not in used), None)
        if vehicle_id is None:
            continue
        used.add(vehicle_id)
        assigned.append(Route(vehicle_id, sequence))
        served.update(sequence)
    unserved = frozenset(set(instance.customer_indices) - served)
    return Solution(
        tuple(sorted(assigned, key=lambda route: route.vehicle_id)),
        unserved=unserved,
    )


def _make_report(
    *,
    instance: Instance,
    solution: Solution,
    budget: Budget,
    status: SolveStatus,
    stop_reason: StopReason,
    stats: SavingsStats,
    start: float,
    cpu_start: float,
    estimated_memory_bytes: int,
) -> SolveReport:
    return SolveReport(
        solver_name="clarke_wright_savings",
        problem_type=instance.problem_type,
        status=status,
        stop_reason=stop_reason,
        objective_value=solution_cost(instance, solution),
        objective_units=instance.matrix.unit,
        wall_time_ms=(time.perf_counter() - start) * 1000.0,
        cpu_time_ms=(time.process_time() - cpu_start) * 1000.0,
        peak_memory_mb=estimated_memory_bytes / (1024 * 1024),
        nodes_created=stats.savings_pairs,
        nodes_explored=stats.pairs_evaluated,
        distance_matrix_hash=instance.matrix.content_hash,
        solver_config_hash=budget.config_hash(),
        extra={
            "construction": "directed_parallel_clarke_wright",
            "savings_pairs": str(stats.savings_pairs),
            "pairs_evaluated": str(stats.pairs_evaluated),
            "merges_accepted": str(stats.merges_accepted),
            "positive_merges": str(stats.positive_merges),
            "initial_routes": str(stats.initial_routes),
            "final_routes": str(stats.final_routes),
            "construction_complete": str(
                status is SolveStatus.HEURISTIC_FEASIBLE_CVRPTW
            ).lower(),
            "instance_infeasibility_proven": "false",
        },
    )


class ClarkeWrightSolver:
    """Fleet-aware directed savings constructor for CVRPTW instances."""

    @property
    def name(self) -> str:
        return "clarke_wright_savings"

    def solve(
        self,
        instance: Instance,
        budget: Budget = UNLIMITED,
    ) -> tuple[Solution, SolveReport]:
        if instance.problem_type is not ProblemType.CVRPTW:
            raise ValueError(
                f"{self.name} currently requires CVRPTW; instance "
                f"'{instance.name}' is {instance.problem_type.value}"
            )

        start = time.perf_counter()
        cpu_start = time.process_time()
        deadline = (
            start + budget.wall_time_ms / 1000.0
            if budget.wall_time_ms is not None
            else None
        )
        customers = instance.customer_indices
        pair_count = len(customers) * max(0, len(customers) - 1)
        estimated_memory = pair_count * _ESTIMATED_BYTES_PER_SAVING
        memory_limit = (
            budget.max_memory_mb * 1024 * 1024
            if budget.max_memory_mb is not None
            else None
        )

        routes: dict[int, tuple[int, ...]] = {
            node: (node,) for node in customers
        }
        owner = {node: node for node in customers}

        if memory_limit is not None and estimated_memory > memory_limit:
            sequences = tuple(routes.values())
            solution = _partial_solution(instance, sequences)
            stats = SavingsStats(
                savings_pairs=0,
                pairs_evaluated=0,
                merges_accepted=0,
                positive_merges=0,
                initial_routes=len(customers),
                final_routes=len(routes),
            )
            return solution, _make_report(
                instance=instance,
                solution=solution,
                budget=budget,
                status=SolveStatus.HEURISTIC_PARTIAL,
                stop_reason=StopReason.MEMORY_CAP,
                stats=stats,
                start=start,
                cpu_start=cpu_start,
                estimated_memory_bytes=estimated_memory,
            )

        depot = instance.depot_index
        savings: list[tuple[int, int, int]] = []
        for left in customers:
            if deadline is not None and time.perf_counter() >= deadline:
                sequences = tuple(routes.values())
                solution = _partial_solution(instance, sequences)
                stats = SavingsStats(
                    savings_pairs=len(savings),
                    pairs_evaluated=0,
                    merges_accepted=0,
                    positive_merges=0,
                    initial_routes=len(customers),
                    final_routes=len(routes),
                )
                return solution, _make_report(
                    instance=instance,
                    solution=solution,
                    budget=budget,
                    status=SolveStatus.HEURISTIC_PARTIAL,
                    stop_reason=StopReason.TIMEOUT,
                    stats=stats,
                    start=start,
                    cpu_start=cpu_start,
                    estimated_memory_bytes=estimated_memory,
                )
            for right in customers:
                if left == right:
                    continue
                saving = (
                    instance.matrix.cost(left, depot)
                    + instance.matrix.cost(depot, right)
                    - instance.matrix.cost(left, right)
                )
                savings.append((saving, left, right))
        savings.sort(key=lambda item: (-item[0], item[1], item[2]))

        evaluated = 0
        merges = 0
        positive_merges = 0
        interruption: StopReason | None = None
        for saving, left, right in savings:
            if deadline is not None and time.perf_counter() >= deadline:
                interruption = StopReason.TIMEOUT
                break
            if budget.max_nodes is not None and evaluated >= budget.max_nodes:
                interruption = StopReason.NODE_CAP
                break
            if len(routes) <= len(instance.vehicles) and saving <= 0:
                break

            evaluated += 1
            left_route_id = owner[left]
            right_route_id = owner[right]
            if left_route_id == right_route_id:
                continue
            left_route = routes[left_route_id]
            right_route = routes[right_route_id]
            if left_route[-1] != left or right_route[0] != right:
                continue
            merged = left_route + right_route
            if not _compatible_vehicle_ids(instance, merged):
                continue

            routes[left_route_id] = merged
            del routes[right_route_id]
            for node in right_route:
                owner[node] = left_route_id
            merges += 1
            if saving > 0:
                positive_merges += 1

        sequences = tuple(sorted(routes.values()))
        full_solution = _assign_all_routes(instance, sequences)
        stats = SavingsStats(
            savings_pairs=len(savings),
            pairs_evaluated=evaluated,
            merges_accepted=merges,
            positive_merges=positive_merges,
            initial_routes=len(customers),
            final_routes=len(routes),
        )

        if interruption is not None:
            solution = full_solution or _partial_solution(instance, sequences)
            # A complete fleet incumbent may exist when a budget ends before
            # the savings scan. Preserve it, but do not claim construction
            # completion or heuristic quality under an unfinished run.
            return solution, _make_report(
                instance=instance,
                solution=solution,
                budget=budget,
                status=SolveStatus.HEURISTIC_PARTIAL,
                stop_reason=interruption,
                stats=stats,
                start=start,
                cpu_start=cpu_start,
                estimated_memory_bytes=estimated_memory,
            )

        if full_solution is not None and check(instance, full_solution).is_feasible:
            return full_solution, _make_report(
                instance=instance,
                solution=full_solution,
                budget=budget,
                status=SolveStatus.HEURISTIC_FEASIBLE_CVRPTW,
                stop_reason=StopReason.COMPLETED,
                stats=stats,
                start=start,
                cpu_start=cpu_start,
                estimated_memory_bytes=estimated_memory,
            )

        solution = _partial_solution(instance, sequences)
        return solution, _make_report(
            instance=instance,
            solution=solution,
            budget=budget,
            status=SolveStatus.HEURISTIC_INFEASIBLE,
            stop_reason=StopReason.INFEASIBLE,
            stats=stats,
            start=start,
            cpu_start=cpu_start,
            estimated_memory_bytes=estimated_memory,
        )
