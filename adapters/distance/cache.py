"""Persistent matrix cache.

Wraps any :class:`~core.distance.protocol.DistanceProvider` and stores completed
matrices on disk, keyed by the provider's identity and the coordinates it was
asked about. Repeated benchmark sweeps over the same instance then cost one
OSRM call instead of hundreds.

The key deliberately includes a provider fingerprint covering every built-in
setting that can affect matrix values. Two providers that disagree about a
route must never share a cache entry, and a cached matrix in seconds must never
be served to a caller expecting metres -- both would be silent corruption rather
than an error.

Coordinates are rounded before hashing so that floating-point noise in the sixth
decimal (~10 cm) does not cause spurious misses.
"""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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
        with self._connection() as conn:
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

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Open one transaction and always close its file descriptor.

        ``sqlite3.Connection``'s own context manager commits or rolls back but
        does not close the connection. Keeping the close in this helper avoids
        leaked descriptors during large benchmark sweeps.
        """
        conn = sqlite3.connect(self._path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

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

    @property
    def cache_fingerprint(self) -> str:
        """Forward the value-producing identity when caches are composed."""
        return f"cached-v1|inner={self._provider_fingerprint()}"

    def _provider_fingerprint(self) -> str:
        """Stable identity for every setting that can change matrix values."""
        fingerprint = getattr(self._inner, "cache_fingerprint", None)
        if fingerprint is None:
            # Backwards-compatible fallback for third-party providers. Built-in
            # providers expose the richer property below.
            fingerprint = f"{self._inner.name}|unit={self._inner.unit.value}"
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ValueError("provider cache_fingerprint must be a non-empty string")
        return fingerprint

    def _key(self, coords: Sequence[Coord]) -> str:
        h = hashlib.sha256()
        h.update(
            f"waybill-cache-v2|{self._provider_fingerprint()}|{len(coords)}|".encode()
        )
        for c in coords:
            h.update(f"{round(c.x, KEY_PRECISION)},{round(c.y, KEY_PRECISION)};".encode())
        return h.hexdigest()

    def build(self, coords: Sequence[Coord]) -> DistanceMatrix:
        key = self._key(coords)
        with self._connection() as conn:
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
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO matrix_cache (key, provider, unit, n, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, self._inner.name, matrix.unit.value, matrix.n, json.dumps(flat)),
            )
        return matrix

    def clear(self) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM matrix_cache")
