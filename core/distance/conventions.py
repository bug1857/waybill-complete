"""TSPLIB edge-weight conventions.

Pure functions -- no I/O, no file parsing. Parsing lives in ``bench/tsplib``.

These formulas are transcribed from the TSPLIB95 specification and must be
reproduced exactly, including their quirks. Two of those quirks matter:

1. TSPLIB's ``nint`` is round-half-away-from-zero, implemented as
   ``(int)(x + 0.5)``. Python's built-in :func:`round` is round-half-to-even
   (banker's rounding), so ``round(2.5) == 2`` while ``nint(2.5) == 3``. Using
   :func:`round` here produces tours that differ from published optima by a
   fraction of a percent -- which looks exactly like a mediocre solver rather
   than like a bug.

2. The GEO convention uses a *truncated* pi (3.141592), not ``math.pi``, and
   coordinates in DDD.MM degrees-minutes form rather than decimal degrees.

Getting either wrong makes every downstream gap number meaningless, which is why
``tests/test_tsplib.py`` scores published optimal tours before anything else runs.
"""

import math
from collections.abc import Callable
from enum import StrEnum

from core.model.geometry import Coord

#: TSPLIB's value of pi. Deliberately not ``math.pi``.
TSPLIB_PI: float = 3.141592

#: Earth radius in km used by the GEO convention.
TSPLIB_EARTH_RADIUS_KM: float = 6378.388


def nint(value: float) -> int:
    """TSPLIB's nearest-integer function: ``(int)(x + 0.5)``.

    Rounds halves away from zero for non-negative input, unlike :func:`round`,
    which rounds halves to even. TSPLIB distances are non-negative; negative
    input is rejected rather than silently truncated toward zero.
    """
    if value < 0.0:
        raise ValueError(f"nint is defined for non-negative values, got {value}")
    return int(value + 0.5)


class EdgeWeightType(StrEnum):
    EUC_2D = "EUC_2D"
    CEIL_2D = "CEIL_2D"
    MAN_2D = "MAN_2D"
    MAX_2D = "MAX_2D"
    ATT = "ATT"
    GEO = "GEO"
    EXPLICIT = "EXPLICIT"


def euc_2d(a: Coord, b: Coord) -> int:
    """Rounded Euclidean distance."""
    dx, dy = a.x - b.x, a.y - b.y
    return nint(math.sqrt(dx * dx + dy * dy))


def ceil_2d(a: Coord, b: Coord) -> int:
    """Euclidean distance rounded up."""
    dx, dy = a.x - b.x, a.y - b.y
    return math.ceil(math.sqrt(dx * dx + dy * dy))


def man_2d(a: Coord, b: Coord) -> int:
    """Manhattan distance."""
    return nint(abs(a.x - b.x) + abs(a.y - b.y))


def max_2d(a: Coord, b: Coord) -> int:
    """Chebyshev distance."""
    return max(nint(abs(a.x - b.x)), nint(abs(a.y - b.y)))


def att(a: Coord, b: Coord) -> int:
    """Pseudo-Euclidean distance used by the ``att`` instances.

    Note the trailing correction: the result is rounded *up* when ``nint``
    rounded down, so the returned value is never below the true value.
    """
    dx, dy = a.x - b.x, a.y - b.y
    rij = math.sqrt((dx * dx + dy * dy) / 10.0)
    tij = nint(rij)
    return tij + 1 if tij < rij else tij


def _geo_to_radians(value: float) -> float:
    """Convert a TSPLIB DDD.MM coordinate to radians."""
    degrees = int(value)
    minutes = value - degrees
    return TSPLIB_PI * (degrees + 5.0 * minutes / 3.0) / 180.0


def geo(a: Coord, b: Coord) -> int:
    """Great-circle distance in km, TSPLIB's spherical formulation.

    ``Coord.x`` is latitude and ``Coord.y`` is longitude, both in DDD.MM form.
    """
    lat_a, lon_a = _geo_to_radians(a.x), _geo_to_radians(a.y)
    lat_b, lon_b = _geo_to_radians(b.x), _geo_to_radians(b.y)

    q1 = math.cos(lon_a - lon_b)
    q2 = math.cos(lat_a - lat_b)
    q3 = math.cos(lat_a + lat_b)
    inner = 0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)
    # Guard against inner drifting fractionally outside acos's domain.
    inner = max(-1.0, min(1.0, inner))
    return int(TSPLIB_EARTH_RADIUS_KM * math.acos(inner) + 1.0)


_DISPATCH: dict[EdgeWeightType, Callable[[Coord, Coord], int]] = {
    EdgeWeightType.EUC_2D: euc_2d,
    EdgeWeightType.CEIL_2D: ceil_2d,
    EdgeWeightType.MAN_2D: man_2d,
    EdgeWeightType.MAX_2D: max_2d,
    EdgeWeightType.ATT: att,
    EdgeWeightType.GEO: geo,
}


def distance_function(kind: EdgeWeightType) -> Callable[[Coord, Coord], int]:
    """Return the pairwise distance function for a coordinate-based convention.

    Raises for ``EXPLICIT``, which supplies its matrix directly and has no
    coordinate formula.
    """
    if kind is EdgeWeightType.EXPLICIT:
        raise ValueError(
            "EXPLICIT instances carry their matrix in the file; there is no "
            "coordinate formula to apply"
        )
    try:
        return _DISPATCH[kind]
    except KeyError:
        raise ValueError(f"unsupported edge weight type: {kind}") from None
