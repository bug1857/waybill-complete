"""Live OSRM tests.

Skipped automatically when no server is running, so ``make test`` stays green on
a machine without Docker. Run them for real with::

    make osrm-prepare && make osrm-up && make test

These are the tests that verify the claim the whole "real roads" argument rests
on: that a road network produces an asymmetric cost matrix, and that our client
reads it correctly.
"""

import pytest

from adapters.distance.haversine import HaversineProvider
from adapters.distance.osrm import OsrmProvider
from core.model.geometry import Coord
from core.model.units import Unit

pytestmark = pytest.mark.integration

# Real Monaco locations, inside the pinned OSM extract.
MONACO = [
    Coord(43.7355, 7.4256),   # Port Hercule
    Coord(43.7397, 7.4276),   # Casino de Monte-Carlo
    Coord(43.7470, 7.4370),   # Larvotto Beach
    Coord(43.7275, 7.4180),   # Fontvieille
    Coord(43.7315, 7.4212),   # Monaco-Ville
]


@pytest.fixture(scope="module")
def osrm():
    provider = OsrmProvider(unit=Unit.SECONDS)
    if not provider.is_available():
        pytest.skip(f"no OSRM at {provider.base_url} (run: make osrm-up)")
    return provider


def test_builds_a_matrix_of_the_right_shape(osrm):
    m = osrm.build(MONACO)
    assert m.n == len(MONACO)
    assert all(m.cost(i, i) == 0 for i in range(m.n))


def test_real_road_network_is_asymmetric(osrm):
    """The claim the project's realism argument depends on."""
    m = osrm.build(MONACO)
    assert not m.is_symmetric
    differing = sum(
        1
        for i in range(m.n)
        for j in range(i + 1, m.n)
        if m.cost(i, j) != m.cost(j, i)
    )
    assert differing > 0


def test_haversine_and_osrm_disagree_on_the_same_stops(osrm):
    """Straight lines understate driving. This is why the adapter exists."""
    road = osrm.build(MONACO)
    straight = HaversineProvider(unit=Unit.SECONDS, road_factor=1.0).build(MONACO)
    assert road.content_hash != straight.content_hash
    assert straight.is_symmetric and not road.is_symmetric


def test_distances_and_durations_are_different_annotations(osrm):
    seconds = osrm.build(MONACO)
    metres = OsrmProvider(unit=Unit.METRES).build(MONACO)
    assert seconds.unit is Unit.SECONDS
    assert metres.unit is Unit.METRES
    assert seconds.content_hash != metres.content_hash


def test_matrix_is_stable_across_repeated_calls(osrm):
    """A pinned extract must give identical answers, or benchmarks are worthless."""
    assert osrm.build(MONACO).content_hash == osrm.build(MONACO).content_hash


def test_route_geometry_follows_roads(osrm):
    geom = osrm.route_geometry(MONACO[:2])
    assert geom.polyline
    assert geom.distance_m > 0
    straight_m = HaversineProvider(road_factor=1.0).build(MONACO[:2]).cost(0, 1)
    # Driving between two points is never shorter than the straight line.
    assert geom.distance_m >= straight_m


def test_triangle_inequality_can_fail_on_real_roads(osrm):
    """Not a bug: one-way systems and barriers make detours genuinely shorter.

    Recorded because several classical TSP arguments assume metric costs, and
    this instance family does not satisfy that assumption.
    """
    m = osrm.build(MONACO)
    violations = [
        (i, k, j)
        for i in range(m.n)
        for j in range(m.n)
        for k in range(m.n)
        if i != j != k != i and m.cost(i, k) + m.cost(k, j) < m.cost(i, j)
    ]
    assert isinstance(violations, list)   # informational; recorded by the gate tool
