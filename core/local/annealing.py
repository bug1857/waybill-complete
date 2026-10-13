"""Seeded simulated annealing over feasibility-checked relocation moves."""

import math
import random
from dataclasses import dataclass

from core.eval.feasibility import check
from core.eval.objective import solution_cost
from core.model.instance import Instance
from core.model.solution import Route, Solution


@dataclass(frozen=True, slots=True)
class AnnealingConfig:
    iterations: int
    initial_temperature: float
    cooling_rate: float = 0.995
    trace_every: int = 50
    minimum_temperature: float = 1e-9

    def __post_init__(self) -> None:
        if not isinstance(self.iterations, int) or isinstance(self.iterations, bool):
            raise TypeError("iterations must be an integer")
        if self.iterations <= 0:
            raise ValueError("iterations must be positive")
        if not math.isfinite(self.initial_temperature) or self.initial_temperature <= 0:
            raise ValueError("initial_temperature must be finite and positive")
        if not math.isfinite(self.cooling_rate) or not 0 < self.cooling_rate <= 1:
            raise ValueError("cooling_rate must be in (0, 1]")
        if not isinstance(self.trace_every, int) or isinstance(self.trace_every, bool):
            raise TypeError("trace_every must be an integer")
        if self.trace_every <= 0:
            raise ValueError("trace_every must be positive")
        if (
            not math.isfinite(self.minimum_temperature)
            or self.minimum_temperature <= 0
        ):
            raise ValueError("minimum_temperature must be finite and positive")


@dataclass(frozen=True, slots=True)
class AnnealingStats:
    seed: int
    iterations: int
    initial_cost: int
    final_cost: int
    best_cost: int
    moves_proposed: int
    moves_accepted: int
    accepted_worsening_moves: int
    infeasible_moves_rejected: int
    best_trace: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class AnnealingResult:
    solution: Solution
    stats: AnnealingStats


def _random_relocation(
    solution: Solution,
    rng: random.Random,
) -> Solution | None:
    nonempty = [
        index for index, route in enumerate(solution.routes) if route.sequence
    ]
    if not nonempty:
        return None

    source_index = rng.choice(nonempty)
    source = solution.routes[source_index]
    source_position = rng.randrange(len(source.sequence))
    node = source.sequence[source_position]
    source_remaining = (
        source.sequence[:source_position] + source.sequence[source_position + 1 :]
    )

    destination_index = rng.randrange(len(solution.routes))
    destination = solution.routes[destination_index]
    destination_sequence = (
        source_remaining
        if source_index == destination_index
        else destination.sequence
    )
    insertion = rng.randrange(len(destination_sequence) + 1)
    candidate_destination = (
        destination_sequence[:insertion]
        + (node,)
        + destination_sequence[insertion:]
    )

    routes = list(solution.routes)
    if source_index == destination_index:
        if candidate_destination == source.sequence:
            return None
        routes[source_index] = Route(source.vehicle_id, candidate_destination)
    else:
        routes[source_index] = Route(source.vehicle_id, source_remaining)
        routes[destination_index] = Route(
            destination.vehicle_id, candidate_destination
        )
    return Solution(tuple(routes), solution.unserved)


def simulated_annealing(
    instance: Instance,
    initial: Solution,
    *,
    seed: int,
    config: AnnealingConfig,
) -> AnnealingResult:
    """Search with a reproducible relocation stream and full acceptance counters.

    The best feasible solution is returned even though the current state is
    intentionally allowed to move uphill. Invalid capacity/window/shift moves are
    rejected before the Metropolis test and counted separately.
    """
    initial_feasibility = check(instance, initial)
    if not initial_feasibility.is_feasible:
        initial_feasibility.raise_if_infeasible()

    rng = random.Random(seed)
    current = initial
    current_cost = solution_cost(instance, current)
    initial_cost = current_cost
    best = current
    best_cost = current_cost
    temperature = config.initial_temperature

    accepted = 0
    accepted_worsening = 0
    infeasible = 0
    trace: list[tuple[int, int]] = [(0, best_cost)]

    for iteration in range(1, config.iterations + 1):
        candidate = _random_relocation(current, rng)
        if candidate is not None:
            if not check(instance, candidate).is_feasible:
                infeasible += 1
            else:
                candidate_cost = solution_cost(instance, candidate)
                delta = candidate_cost - current_cost
                accept = delta <= 0
                if delta > 0:
                    accept = rng.random() < math.exp(-delta / temperature)
                if accept:
                    current = candidate
                    current_cost = candidate_cost
                    accepted += 1
                    if delta > 0:
                        accepted_worsening += 1
                    if current_cost < best_cost:
                        best = current
                        best_cost = current_cost

        temperature = max(
            config.minimum_temperature,
            temperature * config.cooling_rate,
        )
        if iteration % config.trace_every == 0 or iteration == config.iterations:
            trace.append((iteration, best_cost))

    return AnnealingResult(
        solution=best,
        stats=AnnealingStats(
            seed=seed,
            iterations=config.iterations,
            initial_cost=initial_cost,
            final_cost=current_cost,
            best_cost=best_cost,
            moves_proposed=config.iterations,
            moves_accepted=accepted,
            accepted_worsening_moves=accepted_worsening,
            infeasible_moves_rejected=infeasible,
            best_trace=tuple(trace),
        ),
    )
