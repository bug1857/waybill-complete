"""Stops and time windows.

All times are integer seconds since the start of the planning horizon. Integer
arithmetic is deliberate: a time window compared with floats will admit an
arrival 0.0001 s late on one run and reject it on the next, and the resulting
bug is close to impossible to find.
"""

from dataclasses import dataclass, field

from core.model.geometry import Coord

#: Sentinel upper bound for "no deadline". Large enough to exceed any realistic
#: horizon (~317 years) while staying far from overflow concerns.
HORIZON_END: int = 10_000_000_000


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """A closed interval ``[earliest, latest]`` in integer seconds.

    Arriving before ``earliest`` is legal -- the vehicle waits. Arriving after
    ``latest`` violates the window.
    """

    earliest: int
    latest: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.earliest, int)
            or isinstance(self.earliest, bool)
            or not isinstance(self.latest, int)
            or isinstance(self.latest, bool)
        ):
            raise TypeError("time window bounds must be integer seconds")
        if self.earliest < 0:
            raise ValueError(f"earliest must be non-negative, got {self.earliest}")
        if self.latest < self.earliest:
            raise ValueError(
                f"latest ({self.latest}) precedes earliest ({self.earliest})"
            )

    @property
    def is_unbounded(self) -> bool:
        return self.earliest == 0 and self.latest >= HORIZON_END

    def contains(self, t: int) -> bool:
        return self.earliest <= t <= self.latest


#: The window that constrains nothing.
ANYTIME = TimeWindow(0, HORIZON_END)


@dataclass(frozen=True, slots=True)
class Stop:
    """A node in the problem: the depot or a customer.

    ``demand`` is in whole parcels. Parcel count is the baseline capacity
    dimension because a violation is verifiable by inspection -- you can count
    the pins on a map. Weight and volume are later extensions.
    """

    id: int
    coord: Coord | None = None
    demand: int = 0
    time_window: TimeWindow = field(default=ANYTIME)
    service_time: int = 0

    def __post_init__(self) -> None:
        for name in ("id", "demand", "service_time"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"stop {name} must be an integer")
        if self.id < 0:
            raise ValueError(f"stop id must be non-negative, got {self.id}")
        if self.demand < 0:
            raise ValueError(f"stop {self.id}: demand must be non-negative")
        if self.service_time < 0:
            raise ValueError(f"stop {self.id}: service_time must be non-negative")

    @property
    def is_constrained_in_time(self) -> bool:
        return not self.time_window.is_unbounded or self.service_time > 0
