"""Distance adapters: Haversine, the OSRM client, and the cache.

The OSRM parsing tests run against a recorded response fixture, so they are
hermetic and need no server. The tests that genuinely require a live OSRM are
marked ``integration`` and skip cleanly when it is not running -- a contributor
without Docker still gets a meaningful suite.
"""

import json
from pathlib import Path

import pytest

from adapters.distance.cache import CachedProvider
from adapters.distance.haversine import (
    DEFAULT_ROAD_FACTOR,
    HaversineProvider,
    haversine_metres,
)
from adapters.distance.osrm import OsrmError, OsrmProvider
from core.model.geometry import Coord
from core.model.units import Unit

FIXTURES = Path(__file__).parent / "fixtures"

MONACO = [
    Coord(43.7355, 7.4256),   # Port Hercule
    Coord(43.7397, 7.4276),   # Casino de Monte-Carlo
    Coord(43.7470, 7.4370),   # Larvotto Beach
]


# --- Haversine -------------------------------------------------------------

def test_haversine_matches_known_distance():
    """Berlin to Paris is about 878 km great-circle."""
    berlin, paris = Coord(52.5200, 13.4050), Coord(48.8566, 2.3522)
    km = haversine_metres(berlin, paris) / 1000
    assert 875 < km < 882


def test_haversine_is_zero_for_identical_points():
    assert haversine_metres(MONACO[0], MONACO[0]) == pytest.approx(0.0)


def test_haversine_provider_is_always_symmetric():
    """The defining limitation: it cannot represent a one-way street."""
    m = HaversineProvider().build(MONACO)
    assert m.is_symmetric


def test_road_factor_scales_distances():
    plain = HaversineProvider(road_factor=1.0).build(MONACO)
    scaled = HaversineProvider(road_factor=2.0).build(MONACO)
    assert scaled.cost(0, 1) == pytest.approx(plain.cost(0, 1) * 2, rel=0.01)


def test_default_road_factor_inflates_straight_line():
    assert DEFAULT_ROAD_FACTOR > 1.0


def test_haversine_seconds_unit_produces_durations():
    m = HaversineProvider(unit=Unit.SECONDS, speed_kmh=36.0).build(MONACO)
    assert m.unit is Unit.SECONDS
    metres = HaversineProvider(unit=Unit.METRES).build(MONACO).cost(0, 1)
    assert m.cost(0, 1) == pytest.approx(metres / 10.0, rel=0.02)   # 36 km/h = 10 m/s


def test_haversine_rejects_tsplib_unit():
    with pytest.raises(ValueError, match="physical units"):
        HaversineProvider(unit=Unit.TSPLIB)


# --- OSRM response parsing (hermetic) --------------------------------------

def test_parses_recorded_table_response():
    payload = json.loads((FIXTURES / "osrm_table_3.json").read_text())
    m = OsrmProvider._to_matrix(payload["durations"], 3, Unit.SECONDS)
    assert m.n == 3
    assert all(m.cost(i, i) == 0 for i in range(3))
    assert m.cost(0, 1) > 0


def test_recorded_real_world_response_is_asymmetric():
    """Real road data is asymmetric. This is the fixture's whole purpose."""
    payload = json.loads((FIXTURES / "osrm_table_3.json").read_text())
    m = OsrmProvider._to_matrix(payload["durations"], 3, Unit.SECONDS)
    assert not m.is_symmetric


def test_null_entry_is_rejected_not_zeroed():
    """A null means unroutable. Turning it into 0 would fake two co-located stops."""
    raw = [[0, None, 5], [3, 0, 4], [6, 2, 0]]
    with pytest.raises(OsrmError, match="cannot route"):
        OsrmProvider._to_matrix(raw, 3, Unit.SECONDS)


def test_wrong_row_count_is_rejected():
    with pytest.raises(OsrmError, match="expected 3 rows"):
        OsrmProvider._to_matrix([[0, 1], [1, 0]], 3, Unit.SECONDS)


def test_ragged_row_is_rejected():
    with pytest.raises(OsrmError, match="expected 3"):
        OsrmProvider._to_matrix([[0, 1, 2], [1, 0], [2, 1, 0]], 3, Unit.SECONDS)


def test_coordinates_are_serialised_lon_lat_not_lat_lon():
    """OSRM takes lon,lat. Reversing it silently routes on another continent."""
    s = OsrmProvider._coord_string([Coord(43.7355, 7.4256)])
    assert s.startswith("7.4256")          # longitude first
    assert "43.7355" in s


def test_unreachable_server_gives_actionable_error():
    provider = OsrmProvider(base_url="http://127.0.0.1:9", timeout_s=1.0)
    with pytest.raises(OsrmError, match="cannot reach OSRM"):
        provider.build(MONACO)


def test_is_available_is_false_when_server_is_down():
    assert OsrmProvider(base_url="http://127.0.0.1:9", timeout_s=1.0).is_available() is False


def test_osrm_rejects_tsplib_unit():
    with pytest.raises(ValueError, match="physical units"):
        OsrmProvider(unit=Unit.TSPLIB)


def test_trivial_sizes_need_no_request():
    provider = OsrmProvider(base_url="http://127.0.0.1:9", timeout_s=1.0)
    assert provider.build([]).n == 0
    assert provider.build([MONACO[0]]).n == 1


# --- Cache -----------------------------------------------------------------

class CountingProvider:
    """Records how many times it was actually asked to compute."""

    def __init__(self, unit=Unit.METRES):
        self.calls = 0
        self._inner = HaversineProvider(unit=unit)
        self._unit = unit

    @property
    def name(self):
        return "counting"

    @property
    def unit(self):
        return self._unit

    def build(self, coords):
        self.calls += 1
        return self._inner.build(coords)


def test_cache_serves_second_request_without_recomputing(tmp_path):
    inner = CountingProvider()
    cached = CachedProvider(inner, tmp_path / "c.sqlite")
    a = cached.build(MONACO)
    b = cached.build(MONACO)
    assert inner.calls == 1
    assert cached.hits == 1 and cached.misses == 1
    assert a.content_hash == b.content_hash


def test_cache_survives_a_new_process(tmp_path):
    db = tmp_path / "c.sqlite"
    first = CountingProvider()
    CachedProvider(first, db).build(MONACO)
    second = CountingProvider()
    CachedProvider(second, db).build(MONACO)
    assert second.calls == 0          # served entirely from disk


def test_different_coordinates_miss(tmp_path):
    inner = CountingProvider()
    cached = CachedProvider(inner, tmp_path / "c.sqlite")
    cached.build(MONACO)
    cached.build([Coord(48.85, 2.35), Coord(48.86, 2.36)])
    assert inner.calls == 2


def test_cache_does_not_mix_units(tmp_path):
    """A matrix in seconds must never be served to a caller expecting metres."""
    db = tmp_path / "c.sqlite"
    metres = CachedProvider(CountingProvider(Unit.METRES), db)
    seconds = CachedProvider(CountingProvider(Unit.SECONDS), db)
    m = metres.build(MONACO)
    s = seconds.build(MONACO)
    assert m.unit is Unit.METRES
    assert s.unit is Unit.SECONDS
    assert seconds.misses == 1        # did not reuse the metres entry


def test_cached_matrix_is_identical_to_uncached(tmp_path):
    plain = HaversineProvider().build(MONACO)
    cached = CachedProvider(HaversineProvider(), tmp_path / "c.sqlite").build(MONACO)
    assert plain.content_hash == cached.content_hash


def test_clear_empties_the_cache(tmp_path):
    inner = CountingProvider()
    cached = CachedProvider(inner, tmp_path / "c.sqlite")
    cached.build(MONACO)
    cached.clear()
    cached.build(MONACO)
    assert inner.calls == 2
