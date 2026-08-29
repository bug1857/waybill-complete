"""The cost matrix.

Held as a flat tuple of Python ints. Integer arithmetic throughout: costs are
whole metres, whole seconds, or whole TSPLIB units, never floats. Rounding
happens once, when the matrix is built, and never again -- so every solver sees
byte-identical costs and two runs can be compared.
"""

import hashlib
from collections.abc import Sequence

from core.model.geometry import Coord
from core.model.units import Unit


class DistanceMatrix:
    """An ``n x n`` integer cost matrix.

    Two properties carry weight beyond simple storage:

    ``is_symmetric``
        Computed once at construction. Several classical operators are only
        valid on symmetric costs -- notably 2-opt, whose constant-time move
        evaluation depends on a reversed path costing the same in both
        directions. Real road networks are asymmetric, so this flag is
        load-bearing rather than informational.

    ``content_hash``
        Identifies the matrix in benchmark manifests. A comparison between two
        solvers that saw different matrices is meaningless; recording the hash
        lets the harness refuse such a comparison instead of trusting the
        operator to remember.
    """

    __slots__ = ("_data", "_n", "_unit", "_is_symmetric", "_hash")

    def __init__(self, data: Sequence[int], n: int, unit: Unit) -> None:
        if n < 0:
            raise ValueError(f"matrix size must be non-negative, got {n}")
        if len(data) != n * n:
            raise ValueError(f"expected {n * n} entries for n={n}, got {len(data)}")

        flat = tuple(data)
        for value in flat:
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"matrix entries must be int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"matrix entries must be non-negative, got {value}")
        for i in range(n):
            if flat[i * n + i] != 0:
                raise ValueError(f"diagonal must be zero; d({i},{i})={flat[i * n + i]}")

        self._data = flat
        self._n = n
        self._unit = unit
        self._is_symmetric = self._compute_symmetry()
        self._hash: str | None = None

    def _compute_symmetry(self) -> bool:
        n, d = self._n, self._data
        for i in range(n):
            for j in range(i + 1, n):
                if d[i * n + j] != d[j * n + i]:
                    return False
        return True

    @classmethod
    def from_coords(
        cls,
        coords: Sequence[Coord],
        distance_fn,
        unit: Unit,
    ) -> "DistanceMatrix":
        """Build a matrix by applying ``distance_fn`` to every ordered pair."""
        n = len(coords)
        data = [0] * (n * n)
        for i in range(n):
            for j in range(n):
                if i != j:
                    data[i * n + j] = distance_fn(coords[i], coords[j])
        return cls(data, n, unit)

    @property
    def n(self) -> int:
        return self._n

    @property
    def unit(self) -> Unit:
        return self._unit

    @property
    def is_symmetric(self) -> bool:
        return self._is_symmetric

    def cost(self, i: int, j: int) -> int:
        return self._data[i * self._n + j]

    def __getitem__(self, key: tuple[int, int]) -> int:
        i, j = key
        return self._data[i * self._n + j]

    @property
    def content_hash(self) -> str:
        """Stable SHA-256 over size, unit, and every entry."""
        if self._hash is None:
            h = hashlib.sha256()
            h.update(f"waybill-matrix-v1|n={self._n}|unit={self._unit.value}|".encode())
            for value in self._data:
                h.update(value.to_bytes(8, "big", signed=False))
            self._hash = h.hexdigest()
        return self._hash

    def __repr__(self) -> str:
        kind = "symmetric" if self._is_symmetric else "asymmetric"
        return (
            f"DistanceMatrix(n={self._n}, unit={self._unit.value}, {kind}, "
            f"hash={self.content_hash[:12]})"
        )
