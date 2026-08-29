"""Units for objective values.

Every objective carries its unit explicitly. A bare "cost" is not reportable:
comparing a distance in metres against a duration in seconds is a category error
that silently produces a plausible-looking number.
"""

from enum import StrEnum


class Unit(StrEnum):
    """The unit an objective value is measured in."""

    METRES = "metres"
    SECONDS = "seconds"
    #: Abstract integer cost produced by a TSPLIB edge-weight convention.
    #: Not convertible to a physical unit -- TSPLIB coordinates are unitless.
    TSPLIB = "tsplib_units"

    @property
    def is_physical(self) -> bool:
        return self is not Unit.TSPLIB
