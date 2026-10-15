"""Checks the live boundary and matrix-derived results, without network fixtures."""

import json
from http.client import HTTPConnection
from http.server import HTTPServer
from itertools import permutations
from threading import Lock, Thread

import pytest

from adapters.distance.haversine import HaversineProvider
from adapters.distance.osrm import OsrmError, OsrmProvider
from api.server import Handler, ROOT, compare_request, solve_request
from core.model.geometry import Coord
from core.model.units import Unit


def test_topic_comparison_uses_one_matrix_and_valid_proof_states(monkeypatch):
    stops = json.loads((ROOT / "data/live/monaco.json").read_text())["stops"]
    builds, original = [], HaversineProvider.build
    def count_build(self, coords):
        builds.append(self.unit)
        return original(self, coords)
    monkeypatch.setattr(HaversineProvider, "build", count_build)
    comparison = compare_request({"stops": stops, "provider": "haversine", "problem": "TSP"})
    results = comparison["results"]
    assert comparison["skipped"] == []
    assert len(builds) == 2  # One cost matrix and one time matrix, shared by all three.
    assert len({r["matrix_metadata"]["sha256"] for r in results}) == 1
    matrix = results[0]["matrix"]
    # Independent small-instance enumeration validates what the comparison may call optimal.
    optimum = min(sum(matrix[a][b] for a, b in zip(tour, tour[1:]))
                  for order in permutations(range(1, len(stops)))
                  for tour in [(0, *order, 0)])
    greedy, branch, crosscheck = results
    assert greedy["report"]["status"] == "HEURISTIC_FEASIBLE_TSP"
    assert greedy["report"]["best_lower_bound"] is None
    assert greedy["report"]["objective_value"] >= optimum
    for exact in (branch, crosscheck):
        assert exact["report"]["status"] == "PROVEN_OPTIMAL_TSP"
        assert exact["report"]["objective_value"] == optimum
        assert exact["report"]["best_lower_bound"] == optimum
    for result in results:
        route = result["routes"][0]
        assert result["feasible"] and not result["unserved"]
        assert sorted(route["sequence"]) == list(range(1, len(stops)))
        assert route["nodes"][0] == route["nodes"][-1] == 0
        assert route["cost"] == sum(matrix[a][b] for a, b in zip(route["nodes"], route["nodes"][1:]))
        assert result["report"]["wall_time_ms"] >= 0


@pytest.mark.parametrize("nodes", [17, 18, 100])
def test_comparison_size_limits_preserve_other_runs(nodes):
    stops = [{"lat": 26.9 + i * .0001, "lon": 75.8 + (i % 3) * .001} for i in range(nodes)]
    result = compare_request({"stops": stops, "provider": "haversine", "solver": "held_karp", "wall_time_ms": 1})
    assert len(result["results"]) == (3 if nodes <= 17 else 2)
    assert len(result["skipped"]) == (0 if nodes <= 17 else 1)
    if result["skipped"]:
        assert result["skipped"][0]["solver"] == "held_karp"
        assert "17 nodes" in result["skipped"][0]["reason"]
    for run in result["results"]:
        assert run["feasible"]
        assert sorted(run["routes"][0]["sequence"]) == list(range(1, nodes))
        assert run["report"]["objective_value"] == sum(run["matrix"][a][b] for a, b in zip(run["routes"][0]["nodes"], run["routes"][0]["nodes"][1:]))


def test_comparison_fleet_only_uses_applicable_solver():
    stops = json.loads((ROOT / "data/live/monaco.json").read_text())["stops"]
    result = compare_request({"stops": stops, "provider": "haversine", "problem": "CVRPTW", "solver": "savings", "vehicles": 2, "capacity": 25})
    assert result["skipped"] == []
    assert len(result["results"]) == 1
    assert result["results"][0]["report"]["solver_name"] == "clarke_wright_savings"


@pytest.mark.parametrize("change", [{"solver": []}, {"solver": "fake"}, {"matrix": []}, {"provider": "remote"}, {"vehicles": 2}, {"wall_time_ms": 2001}, {"solver": "savings"}])
def test_comparison_rejects_bad_inputs(change):
    with pytest.raises(ValueError):
        compare_request({"stops": [{"lat": 26.9, "lon": 75.8}, {"lat": 26.91, "lon": 75.81}], "provider": "haversine", **change})


def test_live_routes_and_schedule():
    stops = json.loads((ROOT / "data/live/monaco.json").read_text())["stops"]
    coords = [Coord(s["lat"], s["lon"]) for s in stops]
    costs = HaversineProvider(unit=Unit.METRES).build(coords)
    times = HaversineProvider(unit=Unit.SECONDS).build(coords)
    for problem, solver in [("TSP", "held_karp"), ("CVRPTW", "savings")]:
        payload = {"stops": stops, "provider": "haversine", "problem": problem,
                   "solver": solver, "vehicles": 1 if problem == "TSP" else 2, "capacity": 2}
        result = solve_request(payload)
        assert result["feasible"] and not result["violations"] and not result["unserved"]
        assert sorted(n for r in result["routes"] for n in r["sequence"]) == list(range(1, len(stops)))
        assert result["report"]["objective_value"] == sum(r["cost"] for r in result["routes"])
        assert result["matrix_metadata"]["sha256"] == result["report"]["distance_matrix_hash"]
        assert len(result["matrix"]) == len(stops)
        for route in result["routes"]:
            assert route["cost"] == sum(costs[a, b] for a, b in zip(route["nodes"], route["nodes"][1:]))
            elapsed, previous = 0, 0
            for index, node in enumerate(route["sequence"]):
                elapsed += times[previous, node]
                assert route["schedule"]["arrival"][index] == elapsed
                elapsed += 120 if problem == "CVRPTW" else 0
                assert route["schedule"]["departure"][index] == elapsed
                previous = node
            assert route["schedule"]["return_to_depot"] == elapsed + times[previous, 0]
            assert route["geometry"] is None
            if problem == "CVRPTW":
                assert route["load"] <= 2
        assert result["provenance"]["time_matrix_sha256"] == times.content_hash
    impossible = solve_request({"stops": stops, "provider": "haversine", "problem": "CVRPTW",
                                "solver": "savings", "vehicles": 1, "capacity": 1})
    assert not impossible["feasible"] and impossible["unserved"]
    assert "INFEASIBLE" in impossible["report"]["status"]


def test_live_rejects_bad_inputs_before_network():
    stops = [{"lat": 43.7, "lon": 7.4}, {"lat": 43.71, "lon": 7.41}]
    for change in [{"solver": []}, {"provider": "remote"}, {"vehicles": True},
                   {"wall_time_ms": 2001}, {"problem": "CVRPTW"},
                   {"stops": stops * 51}, {"osrm_url": "http://example.com"},
                   {"stops": [stops[0], {"lat": 10 ** 400, "lon": 0}]},
                   {"stops": [stops[0], {"lat": float("nan"), "lon": 0}]},
                   {"stops": [stops[0], {**stops[1], "service_time": 1}]}]:
        with pytest.raises(ValueError):
            solve_request({"stops": stops, **change})


@pytest.mark.parametrize("operation", [solve_request, compare_request])
def test_pinned_monaco_router_rejects_outside_coverage_before_network(monkeypatch, operation):
    def network_must_not_run(*_):
        pytest.fail("out-of-coverage coordinates reached OSRM")
    monkeypatch.setattr(OsrmProvider, "build", network_must_not_run)
    with pytest.raises(ValueError, match="Monaco.*estimate"):
        operation({"stops": [{"lat": 26.9124, "lon": 75.7873}, {"lat": 26.9239, "lon": 75.8267}], "provider": "osrm"}, dataset_id="monaco-260901:test")


def test_estimates_remain_available_outside_monaco():
    result = solve_request({"stops": [{"lat": 26.9124, "lon": 75.7873}, {"lat": 26.9239, "lon": 75.8267}], "provider": "haversine"}, dataset_id="monaco-260901:test")
    assert result["feasible"] and result["report"]["objective_value"] > 0


@pytest.mark.parametrize("operation", [solve_request, compare_request])
@pytest.mark.parametrize("stops", [
    [{"lat": 28.63, "lon": 77.22}, {"lat": 28.64, "lon": 77.23}],
    [{"lat": 26.9124, "lon": 75.7873}, {"lat": 43.7355, "lon": 7.4256}],
    [{"lat": 26.9239, "lon": 75.8267}, {"lat": 27.14, "lon": 75.8267}],
])
def test_combined_router_rejects_outside_or_mixed_regions_before_network(monkeypatch, operation, stops):
    monkeypatch.setattr(OsrmProvider, "build", lambda *_: pytest.fail("unsupported trip reached OSRM"))
    with pytest.raises(ValueError, match="Monaco.*Jaipur.*estimate"):
        operation({"stops": stops, "provider": "osrm"}, dataset_id="monaco-jaipur-261013:test")


@pytest.mark.parametrize("stops", [
    [{"lat": 26.9124, "lon": 75.7873}, {"lat": 26.9239, "lon": 75.8267}],
    [{"lat": 26.84, "lon": 75.56}, {"lat": 26.83, "lon": 75.80}],
    [{"lat": 26.72, "lon": 75.50}, {"lat": 27.13, "lon": 76.02}],
    [{"lat": 43.7355, "lon": 7.4256}, {"lat": 43.7397, "lon": 7.4276}],
])
def test_combined_router_accepts_one_supported_region(monkeypatch, stops):
    monkeypatch.setattr(OsrmProvider, "build", lambda self, coords: HaversineProvider(unit=self.unit).build(coords))
    def missing_geometry(*_):
        raise OsrmError("test-only geometry unavailable")
    monkeypatch.setattr(OsrmProvider, "route_geometry", missing_geometry)
    result = compare_request({"stops": stops, "provider": "osrm"}, dataset_id="monaco-jaipur-261013:test")
    assert len(result["results"]) == 3
    assert all(r["feasible"] and r["report"]["objective_value"] > 0 for r in result["results"])


def test_live_http_boundary():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.osrm_url, server.dataset_id = "http://127.0.0.1:1", None
    server.public_origin = "https://waybill.test"
    server.solve_lock = Lock()
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("GET", "/api/example")
        response = client.getresponse()
        assert response.status == 200
        stops = json.loads(response.read())["stops"]
        client.request("GET", "/api/example", headers={"Host": "waybill.test", "Origin": server.public_origin})
        response = client.getresponse()
        assert response.status == 200
        response.read()
        client.request("GET", "/api/example", headers={"Host": "waybill.test", "Origin": "https://waybill.test.evil"})
        response = client.getresponse()
        assert response.status == 403
        response.read()
        server.solve_lock.acquire()
        try:
            for path in ("/api/solve", "/api/compare"):
                client.request("POST", path, "{}", {"Content-Type": "application/json"})
                response = client.getresponse()
                assert response.status == 429
                response.read()
            client.request("HEAD", "/live.html")
            response = client.getresponse()
            assert response.status == 200
            response.read()
        finally:
            server.solve_lock.release()
        client.request("POST", "/api/solve", json.dumps({"stops": stops, "provider": "haversine"}),
                       {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200 and json.loads(response.read())["feasible"]
        client.request("POST", "/api/compare", json.dumps({"stops": stops, "provider": "haversine"}), {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200 and len(json.loads(response.read())["results"]) == 3
        client.request("GET", "/route-comparison.js?v=1")
        response = client.getresponse()
        assert response.status == 200 and b"WaybillComparison" in response.read()
        for method in ("GET", "HEAD"):
            client.request(method, "/map-context.js?v=1")
            response = client.getresponse()
            assert response.status == 200
            body = response.read()
            if method == "GET":
                assert b"WaybillMap" in body
        client.request("POST", "/api/compare", "{}", {"Content-Type": "application/json", "Origin": "https://evil.example"})
        response = client.getresponse()
        assert response.status == 403
        response.read()
        for headers in [{"Origin": "https://evil.example"}, {"Host": "evil.example"}]:
            client.request("POST", "/api/solve", "{}", {"Content-Type": "application/json", **headers})
            response = client.getresponse()
            assert response.status == 403
            response.read()
        client.request("POST", "/api/solve", "{}", {"Content-Type": "application/json", "Content-Length": "65537"})
        response = client.getresponse()
        assert response.status == 413
        response.read()
        client.request("HEAD", "/../README.md")
        response = client.getresponse()
        assert response.status == 404
        response.read()
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        worker.join()


def test_live_osrm_geometry():
    if not OsrmProvider(timeout_s=1).is_available():
        pytest.skip("local OSRM unavailable")
    stops = json.loads((ROOT / "data/live/monaco.json").read_text())["stops"]
    result = solve_request({"stops": stops, "provider": "osrm", "solver": "held_karp"})
    assert result["feasible"] and not result["warnings"]
    assert result["provenance"]["geometry_kind"] == "road"
    assert all(r["geometry"]["polyline"] for r in result["routes"])
    assert all(len(r["geometry"]["leg_polylines"]) == len(r["nodes"]) - 1 for r in result["routes"])
    assert all(all(leg for leg in r["geometry"]["leg_polylines"]) for r in result["routes"])
    matrix = OsrmProvider(unit=Unit.METRES).build([Coord(s["lat"], s["lon"]) for s in stops])
    assert result["report"]["distance_matrix_hash"] == matrix.content_hash
    assert result["report"]["objective_value"] == sum(matrix[a, b] for r in result["routes"] for a, b in zip(r["nodes"], r["nodes"][1:]))


def test_hosted_commit_identity_requires_no_git_and_valid_commit(monkeypatch, tmp_path):
    import api.server as api
    from bench.evidence.provenance import ProvenanceError

    stops = json.loads((ROOT / "data/live/monaco.json").read_text())["stops"]
    monkeypatch.setattr(api, "ROOT", tmp_path)
    def unavailable(_):
        raise ProvenanceError("no git checkout")
    monkeypatch.setattr(api, "capture_git_state", unavailable)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)
    payload = {"stops": stops, "provider": "haversine"}
    result = solve_request(payload)
    assert result["provenance"]["git_revision"] == "a" * 40
    assert not result["provenance"]["git_dirty"]
    monkeypatch.setenv("RENDER_GIT_COMMIT", "unknown")
    with pytest.raises(ProvenanceError):
        solve_request(payload)
