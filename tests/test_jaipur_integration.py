"""Opt-in full hosted-container checks, not mock road-routing evidence.

Run with WAYBILL_JAIPUR_API=http://127.0.0.1:8006 against the built image
configured with RENDER_EXTERNAL_URL=https://waybill.test. Coordinate fixtures
exercise the centre, airport and western coverage; they are not real orders.
"""

import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import pytest

pytestmark = pytest.mark.integration
STOPS = [
    {"lat": 26.9124, "lon": 75.7873},
    {"lat": 26.9239299, "lon": 75.8268692},
    {"lat": 26.8281087, "lon": 75.8079888},
    {"lat": 26.8423537, "lon": 75.5617643},
]


@pytest.fixture
def request_api():
    base = os.environ.get("WAYBILL_JAIPUR_API")
    if not base:
        pytest.skip("set WAYBILL_JAIPUR_API to the built Jaipur/Monaco image")
    host = "waybill.test" if urlsplit(base).hostname in ("127.0.0.1", "localhost") else urlsplit(base).netloc

    def request(path, payload=None):
        req = Request(base.rstrip("/") + path, data=None if payload is None else json.dumps(payload).encode(),
                      headers={"Host": host, "Content-Type": "application/json"})
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    return request


def assert_run(run, nodes):
    assert run["feasible"] and not run["unserved"] and not run["violations"]
    assert sorted(node for route in run["routes"] for node in route["sequence"]) == list(range(1, nodes))
    cost = sum(run["matrix"][a][b] for route in run["routes"] for a, b in zip(route["nodes"], route["nodes"][1:]))
    assert cost == run["report"]["objective_value"] > 0
    assert run["provenance"]["geometry_kind"] == "road"
    assert "monaco-jaipur-" in run["provenance"]["provider_fingerprint"]
    assert all(route["geometry"]["polyline"] for route in run["routes"])


def test_jaipur_image_health_and_coverage(request_api):
    health = request_api("/api/health")
    assert health["osrm_available"] and health["dataset_id"].startswith("monaco-jaipur-")
    options = request_api("/api/places/options")
    assert set(options["road_regions"]) == {"monaco", "jaipur"}
    assert options["regions"]["jaipur"]["roads"]
    assert not options["regions"]["delhi"]["roads"]


def test_jaipur_suburbs_three_way_road_comparison(request_api):
    data = request_api("/api/compare", {"stops": STOPS, "provider": "osrm", "wall_time_ms": 1000})
    assert len(data["results"]) == 3 and not data["skipped"]
    assert len({run["matrix_metadata"]["sha256"] for run in data["results"]}) == 1
    for run in data["results"]:
        assert_run(run, len(STOPS))
        assert not run["matrix_metadata"]["symmetric"]
    assert data["results"][1]["report"]["status"] == "PROVEN_OPTIMAL_TSP"
    assert data["results"][1]["report"]["objective_value"] == data["results"][2]["report"]["objective_value"]


def test_combined_image_preserves_monaco(request_api):
    example = request_api("/api/example")
    data = request_api("/api/compare", {"stops": example["stops"], "provider": "osrm"})
    for run in data["results"]:
        assert_run(run, len(example["stops"]))
    assert [r["report"]["objective_value"] for r in data["results"]] == [10792, 9547, 9547]


def test_jaipur_100_node_synthetic_stress(request_api):
    stops = [{"lat": 26.900 + (i // 10) * .002, "lon": 75.795 + (i % 10) * .002} for i in range(100)]
    assert_run(request_api("/api/solve", {"stops": stops, "provider": "osrm"}), len(stops))
