"""Persistent matrix cache.

Wraps any :class:`~core.distance.protocol.DistanceProvider` and stores completed
matrices on disk, keyed by the provider's identity and the coordinates it was
asked about. Repeated benchmark sweeps over the same instance then cost one
OSRM call instead of hundreds.

The key deliberately includes the provider name and unit. Two providers that
disagree about a route must never share a cache entry, and a cached matrix in
seconds must never be served to a caller expecting metres -- both would be
silent corruption rather than an error.

Coordinates are rounded before hashing so that floating-point noise in the sixth
decimal (~10 cm) does not cause spurious misses.
"""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.units import Unit

#: Coordinate rounding used in cache keys: 6 dp is ~0.11 m at the equator.
KEY_PRECISION: int = 6


class CachedProvider:
    """Memoises another provider's matrices in a SQLite file."""

    def __init__(self, inner, path: Path | str) -> None:
        self._inner = inner
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matrix_cache (
                    key         TEXT PRIMARY KEY,
                    provider    TEXT NOT NULL,
                    unit        TEXT NOT NULL,
                    n           INTEGER NOT NULL,
                    data        TEXT NOT NULL,
                    created_at  REAL DEFAULT (julianday('now'))
                )
                """
            )

    @property
    def name(self) -> str:
        return f"cached({self._inner.name})"

    @property
    def unit(self) -> Unit:
        return self._inner.unit

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def _key(self, coords: Sequence[Coord]) -> str:
        h = hashlib.sha256()
        h.update(f"{self._inner.name}|{self._inner.unit.value}|{len(coords)}|".encode())
        for c in coords:
            h.update(f"{round(c.x, KEY_PRECISION)},{round(c.y, KEY_PRECISION)};".encode())
        return h.hexdigest()

    def build(self, coords: Sequence[Coord]) -> DistanceMatrix:
        key = self._key(coords)
        with sqlite3.connect(self._path) as conn:
            row = conn.execute(
                "SELECT n, unit, data FROM matrix_cache WHERE key = ?", (key,)
            ).fetchone()

        if row is not None:
            n, unit_value, payload = row
            self._hits += 1
            return DistanceMatrix(json.loads(payload), n, Unit(unit_value))

        self._misses += 1
        matrix = self._inner.build(coords)
        flat = [matrix.cost(i, j) for i in range(matrix.n) for j in range(matrix.n)]
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO matrix_cache (key, provider, unit, n, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, self._inner.name, matrix.unit.value, matrix.n, json.dumps(flat)),
            )
        return matrix

    def clear(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute("DELETE FROM matrix_cache")
