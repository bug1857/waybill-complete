"""Checks the live boundary and matrix-derived results, without network fixtures."""

import json
from http.client import HTTPConnection
from http.server import HTTPServer
from itertools import permutations
from threading import Thread

import pytest

from adapters.distance.haversine import HaversineProvider
from adapters.distance.osrm import OsrmProvider
from api.server import Handler, ROOT, solve_request
from core.model.geometry import Coord
from core.model.units import Unit


def test_topic_comparison_uses_one_matrix_and_valid_proof_states():
    stops = json.loads((ROOT / "data/live/monaco.json").read_text())["stops"]
    results = [solve_request({"stops": stops, "provider": "haversine", "problem": "TSP", "solver": name})
               for name in ("nearest_neighbor", "branch_and_bound", "held_karp")]
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


def test_live_http_boundary():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.osrm_url, server.dataset_id = "http://127.0.0.1:1", None
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("GET", "/api/example")
        response = client.getresponse()
        assert response.status == 200
        stops = json.loads(response.read())["stops"]
        client.request("POST", "/api/solve", json.dumps({"stops": stops, "provider": "haversine"}),
                       {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200 and json.loads(response.read())["feasible"]
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
