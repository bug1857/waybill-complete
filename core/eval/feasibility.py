"""The independent feasibility checker.

This module deliberately shares no code with any solver. Solvers are supposed to
respect constraints; this exists because they sometimes do not, and the failure
is silent. The bug class it catches: a local-search move that improves distance
while pushing an arrival past its time window. Without an independent checker
that surfaces as a mysteriously good result; with one it is a failing test.

Every solver's output passes through here before it may be reported, and no
result is stamped feasible on a solver's own say-so.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from core.model.instance import Instance
from core.model.solution import Route, Solution


class ViolationKind(StrEnum):
    UNVISITED_CUSTOMER = "unvisited_customer"
    UNSERVED_CUSTOMER = "unserved_customer"
    INVALID_UNSERVED_NODE = "invalid_unserved_node"
    DUPLICATE_VISIT = "duplicate_visit"
    DEPOT_IN_ROUTE = "depot_in_route"
    UNKNOWN_NODE = "unknown_node"
    UNKNOWN_VEHICLE = "unknown_vehicle"
    VEHICLE_REUSED = "vehicle_reused"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    TIME_WINDOW_MISSED = "time_window_missed"
    SHIFT_EXCEEDED = "shift_exceeded"
    DURATION_EXCEEDED = "duration_exceeded"


@dataclass(frozen=True, slots=True)
class Violation:
    kind: ViolationKind
    detail: str
    route_index: int | None = None
    node: int | None = None

    def __str__(self) -> str:
        where = ""
        if self.route_index is not None:
            where = f" [route {self.route_index}]"
        if self.node is not None:
            where += f" [node {self.node}]"
        return f"{self.kind.value}{where}: {self.detail}"


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    violations: tuple[Violation, ...]

    @property
    def is_feasible(self) -> bool:
        return not self.violations

    def raise_if_infeasible(self) -> None:
        if self.violations:
            listed = "\n  ".join(str(v) for v in self.violations)
            raise InfeasibleSolution(f"solution is infeasible:\n  {listed}")

    def __str__(self) -> str:
        if self.is_feasible:
            return "feasible"
        return f"{len(self.violations)} violation(s)"


class InfeasibleSolution(Exception):
    """Raised when an infeasible solution is used where a valid one is required."""


@dataclass(frozen=True, slots=True)
class RouteSchedule:
    """Reconstructed timing for one route, for ETA reporting and debugging."""

    arrival: tuple[int, ...]
    departure: tuple[int, ...]
    wait: tuple[int, ...]
    return_to_depot: int


def check(instance: Instance, solution: Solution) -> FeasibilityReport:
    """Check every active constraint and return all violations found.

    Collects violations rather than stopping at the first, because a solver bug
    usually produces several and seeing them together identifies the cause.
    """
    violations: list[Violation] = []
    n = instance.n
    depot = instance.depot_index

    vehicles_by_id = {v.id: v for v in instance.vehicles}
    seen_vehicles: set[int] = set()
    visit_counts: dict[int, int] = {}

    for idx, route in enumerate(solution.routes):
        if route.vehicle_id not in vehicles_by_id:
            violations.append(
                Violation(
                    ViolationKind.UNKNOWN_VEHICLE,
                    f"no vehicle with id {route.vehicle_id}",
                    route_index=idx,
                )
            )
            continue
        if route.vehicle_id in seen_vehicles:
            violations.append(
                Violation(
                    ViolationKind.VEHICLE_REUSED,
                    f"vehicle {route.vehicle_id} drives more than one route",
                    route_index=idx,
                )
            )
        seen_vehicles.add(route.vehicle_id)

        for node in route.sequence:
            if not 0 <= node < n:
                violations.append(
                    Violation(
                        ViolationKind.UNKNOWN_NODE,
                        f"node {node} is outside 0..{n - 1}",
                        route_index=idx,
                        node=node,
                    )
                )
                continue
            if node == depot:
                violations.append(
                    Violation(
                        ViolationKind.DEPOT_IN_ROUTE,
                        "depot must not appear in a route sequence; it is implicit",
                        route_index=idx,
                        node=node,
                    )
                )
                continue
            visit_counts[node] = visit_counts.get(node, 0) + 1

        vehicle = vehicles_by_id[route.vehicle_id]
        violations.extend(_check_capacity(instance, route, vehicle, idx))
        if instance.has_time_constraints:
            violations.extend(_check_timing(instance, route, vehicle, idx))

    for node, count in visit_counts.items():
        if count > 1:
            violations.append(
                Violation(
                    ViolationKind.DUPLICATE_VISIT,
                    f"visited {count} times across routes",
                    node=node,
                )
            )

    for node in solution.unserved:
        if node == depot:
            violations.append(
                Violation(
                    ViolationKind.INVALID_UNSERVED_NODE,
                    "the depot cannot be declared unserved",
                    node=node,
                )
            )
        elif node >= n:
            violations.append(
                Violation(
                    ViolationKind.INVALID_UNSERVED_NODE,
                    f"node {node} is outside 0..{n - 1}",
                    node=node,
                )
            )

    for node in instance.customer_indices:
        if visit_counts.get(node, 0) != 0:
            continue
        if node in solution.unserved:
            violations.append(
                Violation(
                    ViolationKind.UNSERVED_CUSTOMER,
                    "declared unserved; complete solutions must serve every customer",
                    node=node,
                )
            )
        else:
            violations.append(
                Violation(
                    ViolationKind.UNVISITED_CUSTOMER,
                    "not in any route",
                    node=node,
                )
            )

    return FeasibilityReport(tuple(violations))


def _check_capacity(
    instance: Instance, route: Route, vehicle, route_index: int
) -> list[Violation]:
    load = sum(
        instance.stops[node].demand
        for node in route.sequence
        if 0 <= node < instance.n
    )
    if load > vehicle.capacity:
        return [
            Violation(
                ViolationKind.CAPACITY_EXCEEDED,
                f"load {load} exceeds capacity {vehicle.capacity}",
                route_index=route_index,
            )
        ]
    return []


def _check_timing(
    instance: Instance, route: Route, vehicle, route_index: int
) -> list[Violation]:
    if route.is_empty:
        return []

    violations: list[Violation] = []
    depot = instance.depot_index
    t = vehicle.shift_start
    prev = depot

    for node in route.sequence:
        if not 0 <= node < instance.n or node == depot:
            continue
        t += instance.travel_time(prev, node)
        window = instance.stops[node].time_window
        if t < window.earliest:
            t = window.earliest
        if t > window.latest:
            violations.append(
                Violation(
                    ViolationKind.TIME_WINDOW_MISSED,
                    f"arrival {t}s is after latest {window.latest}s",
                    route_index=route_index,
                    node=node,
                )
            )
        t += instance.stops[node].service_time
        prev = node

    t += instance.travel_time(prev, depot)

    if t > vehicle.shift_end:
        violations.append(
            Violation(
                ViolationKind.SHIFT_EXCEEDED,
                f"returns at {t}s, after shift end {vehicle.shift_end}s",
                route_index=route_index,
            )
        )
    if vehicle.max_route_duration is not None:
        duration = t - vehicle.shift_start
        if duration > vehicle.max_route_duration:
            violations.append(
                Violation(
                    ViolationKind.DURATION_EXCEEDED,
                    f"duration {duration}s exceeds max {vehicle.max_route_duration}s",
                    route_index=route_index,
                )
            )
    return violations


def schedule(instance: Instance, route: Route, vehicle) -> RouteSchedule:
    """Reconstruct arrival, wait, and departure times for ETA reporting.

    Uses the same matrix the solver used -- ETAs derived from a different
    distance source would not correspond to the plan they describe.
    """
    arrival: list[int] = []
    departure: list[int] = []
    wait: list[int] = []

    t = vehicle.shift_start
    prev = instance.depot_index
    for node in route.sequence:
        t += instance.travel_time(prev, node)
        arrival.append(t)
        window = instance.stops[node].time_window
        waited = max(0, window.earliest - t)
        wait.append(waited)
        t += waited + instance.stops[node].service_time
        departure.append(t)
        prev = node

    return RouteSchedule(
        arrival=tuple(arrival),
        departure=tuple(departure),
        wait=tuple(wait),
        return_to_depot=t + instance.travel_time(prev, instance.depot_index),
    )
