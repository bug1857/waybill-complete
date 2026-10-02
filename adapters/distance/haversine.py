"""Great-circle distance with a road-detour factor.

The offline fallback. It exists so the entire solver suite runs with no network,
no Docker, and no OSM data -- which is what keeps the test suite fast and
hermetic, and what lets someone clone this repository and reproduce the
algorithmic results without any infrastructure.

It is deliberately *not* the default for real work. Two properties make it a
poor model of a road network, and both matter to the algorithms:

* It is **symmetric**. Real driving is not: one-way streets mean d(A,B) != d(B,A).
* It **understates** real driving distance, typically by 20-40% in a city, because
  vehicles cannot travel in straight lines through buildings.

The ``road_factor`` multiplier compensates for the second in a crude average
sense. It cannot compensate for the first, which is why the asymmetry-sensitive
operators are exercised against OSRM rather than against this.
"""

import math
from collections.abc import Sequence

from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.units import Unit

EARTH_RADIUS_M: float = 6_371_008.8

#: Ratio of real driving distance to straight-line distance in a typical urban
#: grid. A rough average, not a substitute for routing on real geometry.
DEFAULT_ROAD_FACTOR: float = 1.3

#: Assumed average speed when converting distance to duration.
DEFAULT_SPEED_KMH: float = 30.0


def haversine_metres(a: Coord, b: Coord) -> float:
    """Great-circle distance in metres. ``Coord.x`` is latitude, ``y`` is longitude."""
    lat1, lon1 = math.radians(a.x), math.radians(a.y)
    lat2, lon2 = math.radians(b.x), math.radians(b.y)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, h)))


class HaversineProvider:
    """Builds a symmetric great-circle matrix, optionally scaled to a road estimate."""

    def __init__(
        self,
        road_factor: float = DEFAULT_ROAD_FACTOR,
        unit: Unit = Unit.METRES,
        speed_kmh: float = DEFAULT_SPEED_KMH,
    ) -> None:
        if not isinstance(unit, Unit):
            raise TypeError("unit must be a Unit")
        if (
            not isinstance(road_factor, (int, float))
            or isinstance(road_factor, bool)
            or not math.isfinite(road_factor)
            or road_factor <= 0
        ):
            raise ValueError("road_factor must be a finite positive number")
        if unit is Unit.TSPLIB:
            raise ValueError("HaversineProvider produces physical units")
        if (
            not isinstance(speed_kmh, (int, float))
            or isinstance(speed_kmh, bool)
            or not math.isfinite(speed_kmh)
            or speed_kmh <= 0
        ):
            raise ValueError("speed_kmh must be a finite positive number")
        self._road_factor = road_factor
        self._unit = unit
        self._speed_kmh = speed_kmh

    @property
    def name(self) -> str:
        return f"haversine(x{self._road_factor:g})"

    @property
    def unit(self) -> Unit:
        return self._unit

    @property
    def cache_fingerprint(self) -> str:
        """Identity of every parameter capable of changing matrix values."""
        return (
            "haversine-v1"
            f"|road_factor={self._road_factor!r}"
            f"|unit={self._unit.value}"
            f"|speed_kmh={self._speed_kmh!r}"
        )

    def build(self, coords: Sequence[Coord]) -> DistanceMatrix:
        n = len(coords)
        data = [0] * (n * n)
        mps = self._speed_kmh * 1000.0 / 3600.0
        for i in range(n):
            for j in range(i + 1, n):
                metres = haversine_metres(coords[i], coords[j]) * self._road_factor
                value = (
                    int(metres + 0.5)
                    if self._unit is Unit.METRES
                    else int(metres / mps + 0.5)
                )
                data[i * n + j] = value
                data[j * n + i] = value          # symmetric by construction
        return DistanceMatrix(data, n, self._unit)
