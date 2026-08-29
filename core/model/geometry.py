"""Coordinates.

Interpretation is decided by the distance convention, not by this type. For
planar conventions (EUC_2D, ATT, ...) ``x`` and ``y`` are cartesian. For GEO they
are latitude and longitude in TSPLIB's DDD.MM degrees-minutes encoding.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coord:
    x: float
    y: float
