"""The distance-provider interface.

This module is the whole reason ``core/`` stays pure. It defines *what* a
distance source must offer; every implementation that touches a socket, a disk,
or a database lives in ``adapters/``. Revision 1 of the architecture asserted
this rule in prose while placing an OSRM client inside ``core/``; the rule is now
structural and is enforced by ``tools/check_purity.py``.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from core.model.geometry import Coord
from core.model.units import Unit


@runtime_checkable
class DistanceProvider(Protocol):
    """Builds a cost matrix over a set of coordinates.

    Implementations may perform I/O. They belong in ``adapters/``.
    """

    @property
    def name(self) -> str:
        """Short provenance string recorded in the SolveReport."""
        ...

    @property
    def unit(self) -> Unit:
        """The unit of the values this provider returns."""
        ...

    def build(self, coords: Sequence[Coord]) -> "object":
        """Return a :class:`~core.distance.matrix.DistanceMatrix` for ``coords``."""
        ...
