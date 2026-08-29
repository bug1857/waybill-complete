"""OSRM client.

Talks to a self-hosted Open Source Routing Machine over HTTP. This is the
adapter that makes the project's distances real: values come from an actual
street network, so they are asymmetric where the roads are one-way, and route
geometry follows streets instead of cutting through buildings.

Self-hosting matters beyond avoiding rate limits. A public demo server may
change its data or its profile between runs, which would silently invalidate a
benchmark comparison; a pinned local extract does not.

Two endpoints carry the system:

``/table``
    The whole ``n x n`` matrix in one request. This is the solver's input.

``/route``
    Encoded polyline geometry for a specific ordered visit sequence. This is what
    the map draws, and it is requested only for display -- never for costing,
    which always comes from the same ``/table`` matrix the solver optimised
    against. Deriving ETAs from a different source than the plan was built on is
    a subtle way to make a demo disagree with itself.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass

from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.units import Unit

DEFAULT_BASE_URL = "http://127.0.0.1:5001"

#: OSRM's table service refuses very large requests by default.
MAX_TABLE_COORDS = 100


class OsrmError(RuntimeError):
    """OSRM was unreachable, or answered with something unusable."""


@dataclass(frozen=True, slots=True)
class RouteGeometry:
    """Road-following geometry for display."""

    polyline: str
    distance_m: int
    duration_s: int


class OsrmProvider:
    """Builds cost matrices from a running OSRM instance.

    ``unit`` selects which OSRM annotation is used: :attr:`Unit.SECONDS` reads
    ``durations``, :attr:`Unit.METRES` reads ``distances``. Requesting one and
    reading the other is a category error the matrix cannot detect, so it is
    decided here, once.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        unit: Unit = Unit.SECONDS,
        profile: str = "driving",
        timeout_s: float = 30.0,
    ) -> None:
        if unit is Unit.TSPLIB:
            raise ValueError("OSRM produces physical units, not TSPLIB units")
        self._base_url = base_url.rstrip("/")
        self._unit = unit
        self._profile = profile
        self._timeout = timeout_s

    @property
    def name(self) -> str:
        return f"osrm({self._profile},{self._unit.value})"

    @property
    def unit(self) -> Unit:
        return self._unit

    @property
    def base_url(self) -> str:
        return self._base_url

    # -- HTTP -------------------------------------------------------------

    def _get(self, url: str) -> dict:
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.URLError as exc:
            raise OsrmError(
                f"cannot reach OSRM at {self._base_url}: {exc.reason}. "
                f"Start it with `make osrm-up`."
            ) from exc
        except json.JSONDecodeError as exc:
            raise OsrmError(f"OSRM returned malformed JSON: {exc}") from exc

        if payload.get("code") != "Ok":
            raise OsrmError(
                f"OSRM error {payload.get('code')}: {payload.get('message', 'no detail')}"
            )
        return payload

    @staticmethod
    def _coord_string(coords: Sequence[Coord]) -> str:
        """OSRM takes ``lon,lat`` -- the reverse of the usual spoken order.

        Getting this backwards does not error; it silently routes somewhere else
        on Earth, so the conversion happens in exactly one place.
        """
        return ";".join(f"{c.y:.6f},{c.x:.6f}" for c in coords)

    def is_available(self) -> bool:
        """Whether the server answers. Used to skip integration tests cleanly."""
        try:
            self._get(
                f"{self._base_url}/route/v1/{self._profile}/"
                f"13.388860,52.517037;13.397634,52.529407"
            )
        except OsrmError:
            return False
        return True

    # -- Provider ---------------------------------------------------------

    def build(self, coords: Sequence[Coord]) -> DistanceMatrix:
        n = len(coords)
        if n == 0:
            return DistanceMatrix([], 0, self._unit)
        if n == 1:
            return DistanceMatrix([0], 1, self._unit)
        if n > MAX_TABLE_COORDS:
            raise OsrmError(
                f"{n} coordinates exceeds the table limit of {MAX_TABLE_COORDS}; "
                f"raise --max-table-size on the server or tile the request"
            )

        annotation = "duration" if self._unit is Unit.SECONDS else "distance"
        url = (
            f"{self._base_url}/table/v1/{self._profile}/"
            f"{self._coord_string(coords)}?annotations={annotation}"
        )
        payload = self._get(url)
        key = "durations" if self._unit is Unit.SECONDS else "distances"
        raw = payload.get(key)
        if raw is None:
            raise OsrmError(f"OSRM response has no '{key}' field")

        return self._to_matrix(raw, n, self._unit)

    @staticmethod
    def _to_matrix(raw: list, n: int, unit: Unit) -> DistanceMatrix:
        """Convert OSRM's float table to an integer matrix.

        OSRM returns floats, and ``null`` for pairs it cannot route between
        (an unreachable island, a coordinate snapped to a disconnected way). A
        null must not silently become zero -- that would look like two stops at
        the same place and would corrupt every tour through them -- so it is
        rejected loudly here.
        """
        if len(raw) != n:
            raise OsrmError(f"expected {n} rows from OSRM, got {len(raw)}")

        data = [0] * (n * n)
        for i, row in enumerate(raw):
            if len(row) != n:
                raise OsrmError(f"row {i} has {len(row)} entries, expected {n}")
            for j, value in enumerate(row):
                if i == j:
                    continue
                if value is None:
                    raise OsrmError(
                        f"OSRM cannot route between coordinate {i} and {j}. "
                        f"One of them is probably not reachable from the road "
                        f"network in this extract."
                    )
                data[i * n + j] = int(float(value) + 0.5)
        return DistanceMatrix(data, n, unit)

    def route_geometry(self, coords: Sequence[Coord]) -> RouteGeometry:
        """Road-following geometry for an ordered visit sequence, for display only."""
        if len(coords) < 2:
            raise ValueError("a route needs at least two coordinates")
        url = (
            f"{self._base_url}/route/v1/{self._profile}/"
            f"{self._coord_string(coords)}?overview=full&geometries=polyline"
        )
        payload = self._get(url)
        routes = payload.get("routes") or []
        if not routes:
            raise OsrmError("OSRM returned no route")
        route = routes[0]
        return RouteGeometry(
            polyline=route["geometry"],
            distance_m=int(route["distance"] + 0.5),
            duration_s=int(route["duration"] + 0.5),
        )
