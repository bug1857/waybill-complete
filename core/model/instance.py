"""Problem instances.

One type covers TSP, CVRP, and CVRPTW. TSP is not a separate model -- it is the
degenerate case with a single unconstrained vehicle and no time windows, and
:attr:`Instance.problem_type` reports which case an instance actually is by
inspecting it rather than by trusting a label.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from core.distance.matrix import DistanceMatrix
from core.model.stop import Stop
from core.model.units import Unit
from core.model.vehicle import Vehicle


class ProblemType(StrEnum):
    TSP = "TSP"
    CVRP = "CVRP"
    CVRPTW = "CVRPTW"


@dataclass(frozen=True, slots=True)
class Instance:
    """A routing problem.

    ``stops`` holds every node including the depot; ``depot_index`` says which
    one it is. Costs come from ``matrix``. When the problem has time
    constraints, travel *times* come from ``time_matrix`` if supplied, otherwise
    from ``matrix`` when its unit is already seconds.
    """

    name: str
    stops: tuple[Stop, ...]
    vehicles: tuple[Vehicle, ...]
    matrix: DistanceMatrix
    depot_index: int = 0
    time_matrix: DistanceMatrix | None = None
    metadata: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.depot_index, int) or isinstance(self.depot_index, bool):
            raise TypeError("depot_index must be an integer")
        if not self.stops:
            raise ValueError("instance must have at least one stop")
        if not self.vehicles:
            raise ValueError("instance must have at least one vehicle")
        if self.matrix.n != len(self.stops):
            raise ValueError(
                f"matrix is {self.matrix.n}x{self.matrix.n} but there are "
                f"{len(self.stops)} stops"
            )
        if not 0 <= self.depot_index < len(self.stops):
            raise ValueError(f"depot_index {self.depot_index} out of range")
        if self.time_matrix is not None:
            if self.time_matrix.n != len(self.stops):
                raise ValueError("time_matrix size does not match stop count")
            if self.time_matrix.unit is not Unit.SECONDS:
                raise ValueError("time_matrix must be in seconds")
        stop_ids = [stop.id for stop in self.stops]
        if len(set(stop_ids)) != len(stop_ids):
            raise ValueError("stop ids must be unique")
        vehicle_ids = [v.id for v in self.vehicles]
        if len(set(vehicle_ids)) != len(vehicle_ids):
            raise ValueError("vehicle ids must be unique")

    @property
    def n(self) -> int:
        """Total node count, depot included."""
        return len(self.stops)

    @property
    def depot(self) -> Stop:
        return self.stops[self.depot_index]

    @property
    def customer_indices(self) -> tuple[int, ...]:
        """Every node index except the depot."""
        return tuple(i for i in range(self.n) if i != self.depot_index)

    @property
    def has_time_constraints(self) -> bool:
        return any(s.is_constrained_in_time for s in self.stops) or any(
            v.has_time_constraints for v in self.vehicles
        )

    @property
    def problem_type(self) -> ProblemType:
        """Classify by inspection, not by declaration."""
        if self.has_time_constraints:
            return ProblemType.CVRPTW
        if len(self.vehicles) > 1 or any(s.demand > 0 for s in self.stops):
            return ProblemType.CVRP
        return ProblemType.TSP

    def travel_time(self, i: int, j: int) -> int:
        """Travel time in seconds between two nodes.

        Raises if the instance carries time constraints but no time source --
        a configuration error, not an infeasibility.
        """
        if self.time_matrix is not None:
            return self.time_matrix.cost(i, j)
        if self.matrix.unit is Unit.SECONDS:
            return self.matrix.cost(i, j)
        raise ValueError(
            f"instance '{self.name}' needs travel times but has no time_matrix "
            f"and its cost matrix is in {self.matrix.unit.value}"
        )

    @staticmethod
    def single_vehicle_tsp(
        name: str,
        stops: Sequence[Stop],
        matrix: DistanceMatrix,
        depot_index: int = 0,
        metadata: Mapping[str, str] | None = None,
    ) -> "Instance":
        """Build the TSP special case: one vehicle, no capacity, no clock."""
        return Instance(
            name=name,
            stops=tuple(stops),
            vehicles=(Vehicle(id=0),),
            matrix=matrix,
            depot_index=depot_index,
            metadata=MappingProxyType(dict(metadata or {})),
        )
