"""Vehicles."""

from dataclasses import dataclass

from core.model.stop import HORIZON_END

#: Capacity standing for "no limit" (used by the TSP special case).
UNLIMITED_CAPACITY: int = 1 << 40


@dataclass(frozen=True, slots=True)
class Vehicle:
    """One vehicle, available for one shift, based at the depot."""

    id: int
    capacity: int = UNLIMITED_CAPACITY
    shift_start: int = 0
    shift_end: int = HORIZON_END
    max_route_duration: int | None = None

    def __post_init__(self) -> None:
        for name in ("id", "capacity", "shift_start", "shift_end"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"vehicle {name} must be an integer")
        if self.max_route_duration is not None and (
            not isinstance(self.max_route_duration, int)
            or isinstance(self.max_route_duration, bool)
        ):
            raise TypeError("vehicle max_route_duration must be an integer when set")
        if self.id < 0:
            raise ValueError(f"vehicle id must be non-negative, got {self.id}")
        if self.capacity < 0:
            raise ValueError(f"vehicle {self.id}: capacity must be non-negative")
        if self.shift_start < 0:
            raise ValueError(f"vehicle {self.id}: shift_start must be non-negative")
        if self.shift_end < self.shift_start:
            raise ValueError(f"vehicle {self.id}: shift ends before it starts")
        if self.max_route_duration is not None and self.max_route_duration < 0:
            raise ValueError(f"vehicle {self.id}: max_route_duration must be >= 0")

    @property
    def has_time_limits(self) -> bool:
        """Whether this vehicle constrains *time* specifically.

        Capacity is deliberately excluded. A capacitated van with an open-ended
        shift needs no clock, and requiring a travel-time matrix for one would
        reject a perfectly well-formed CVRP instance.
        """
        return (
            self.shift_start != 0
            or self.shift_end < HORIZON_END
            or self.max_route_duration is not None
        )

    @property
    def has_time_constraints(self) -> bool:
        """Whether feasibility depends on a clock, independent of capacity."""
        return (
            self.shift_start != 0
            or self.shift_end < HORIZON_END
            or self.max_route_duration is not None
        )
