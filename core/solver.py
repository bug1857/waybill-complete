"""The solver interface.

Every solver -- brute force, Branch & Bound, simulated annealing -- implements
this one protocol, so the benchmark harness and the API treat all of them
identically and adding a solver requires changing nothing else.

The budget is part of the interface rather than a constructor detail because
exact-versus-heuristic comparison is only fair when both ran under the same
stated limit, and because a solver must be able to report *why* it stopped.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Protocol, runtime_checkable

from core.model.instance import Instance
from core.model.solution import Solution
from core.reporting.report import SolveReport


@dataclass(frozen=True, slots=True)
class Budget:
    """Limits a solver must respect and report against.

    ``None`` means unlimited for that dimension. An unlimited wall clock is
    appropriate only for exact runs on instances small enough to finish.
    """

    wall_time_ms: int | None = None
    max_nodes: int | None = None
    max_memory_mb: int | None = None

    def __post_init__(self) -> None:
        for name in ("wall_time_ms", "max_nodes", "max_memory_mb"):
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer when set")
            if value <= 0:
                raise ValueError(f"{name} must be positive when set, got {value}")

    @property
    def is_unlimited(self) -> bool:
        return (
            self.wall_time_ms is None
            and self.max_nodes is None
            and self.max_memory_mb is None
        )

    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


UNLIMITED = Budget()


@runtime_checkable
class Solver(Protocol):
    """Produces a solution and a full account of how it was produced."""

    @property
    def name(self) -> str:
        """Stable identifier recorded in every SolveReport and benchmark row."""
        ...

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        """Solve ``instance`` within ``budget``.

        Must return a report whose ``status`` and ``stop_reason`` describe what
        actually happened -- a solver that ran out of time reports a timeout, it
        does not report the incumbent as though it were proven.
        """
        ...
