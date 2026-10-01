"""Solutions.

A solution is a set of routes plus an explicit record of anything not served.
"Unserved" is never implicit: a customer missing from every route without
appearing in ``unserved`` is a bug, and the feasibility checker reports it.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Route:
    """One vehicle's ordered customer visits.

    The depot is implicit at both ends and must not appear in ``sequence``.
    """

    vehicle_id: int
    sequence: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.vehicle_id, int) or isinstance(self.vehicle_id, bool):
            raise TypeError("route vehicle_id must be an integer")
        if self.vehicle_id < 0:
            raise ValueError("route vehicle_id must be non-negative")
        for node in self.sequence:
            if not isinstance(node, int) or isinstance(node, bool):
                raise TypeError("route node indices must be integers")
            if node < 0:
                raise ValueError(f"route node index must be non-negative, got {node}")
        if len(set(self.sequence)) != len(self.sequence):
            raise ValueError(
                f"vehicle {self.vehicle_id}: route visits a node more than once"
            )

    @property
    def is_empty(self) -> bool:
        return not self.sequence

    def __len__(self) -> int:
        return len(self.sequence)


@dataclass(frozen=True, slots=True)
class Solution:
    routes: tuple[Route, ...]
    unserved: frozenset[int] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for node in self.unserved:
            if not isinstance(node, int) or isinstance(node, bool):
                raise TypeError("unserved node indices must be integers")
            if node < 0:
                raise ValueError(
                    f"unserved node index must be non-negative, got {node}"
                )
        overlap = set(self.served).intersection(self.unserved)
        if overlap:
            listed = ", ".join(str(node) for node in sorted(overlap))
            raise ValueError(f"nodes cannot be both served and unserved: {listed}")

    @property
    def served(self) -> tuple[int, ...]:
        return tuple(node for route in self.routes for node in route.sequence)

    @property
    def used_vehicle_count(self) -> int:
        return sum(1 for r in self.routes if not r.is_empty)

    @staticmethod
    def single_tour(tour: Iterable[int], vehicle_id: int = 0) -> "Solution":
        """Wrap a TSP tour (customers only, depot implicit) as a Solution."""
        return Solution(routes=(Route(vehicle_id=vehicle_id, sequence=tuple(tour)),))
