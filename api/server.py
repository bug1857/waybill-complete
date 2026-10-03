"""Courier workbench; loopback by default, with an explicit hosted origin."""

import argparse
import hashlib
import json
import math
import os
import re
import time
from dataclasses import asdict
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

from adapters.distance.haversine import HaversineProvider
from adapters.distance.osrm import OsrmError, OsrmProvider
from adapters.places import PlacesBusy, PlacesError, fetch_places, places_options
from bench.evidence.provenance import GitState, ProvenanceError, capture_git_state
from core.construct import ClarkeWrightSolver, NearestNeighborSolver
from core.eval.feasibility import check, schedule
from core.eval.objective import route_cost
from core.exact import BranchAndBoundSolver, HeldKarpSolver
from core.model.geometry import Coord
from core.model.instance import Instance
from core.model.stop import Stop, TimeWindow
from core.model.units import Unit
from core.model.vehicle import Vehicle
from core.solver import Budget

ROOT = Path(__file__).resolve().parent.parent
MAX_BODY_BYTES = 64 * 1024
SOLVERS = {
    "nearest_neighbor": NearestNeighborSolver,
    "held_karp": HeldKarpSolver,
    "branch_and_bound": BranchAndBoundSolver,
    "savings": ClarkeWrightSolver,
}


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return value


def coordinate(value, name, limit):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not -limit <= value <= limit or not math.isfinite(value):
        raise ValueError(f"{name} must be finite and within ±{limit}")
    return value


def _prepare_request(payload, *, osrm_url, dataset_id):
    fields = {"stops", "problem", "solver", "provider", "vehicles", "capacity", "shift_end", "wall_time_ms"}
    if not isinstance(payload, dict) or set(payload) - fields:
        raise ValueError("request must be an object containing only supported fields")
    raw_stops = payload.get("stops")
    if not isinstance(raw_stops, list) or not 2 <= len(raw_stops) <= 100:
        raise ValueError("stops must contain 2–100 nodes, with the depot first")
    problem = payload.get("problem", "TSP")
    solver_name = payload.get("solver", "nearest_neighbor")
    provider_name = payload.get("provider", "osrm")
    if not isinstance(solver_name, str) or problem not in ("TSP", "CVRPTW") or solver_name not in SOLVERS:
        raise ValueError("choose a supported problem and solver")
    if (problem == "CVRPTW") != (solver_name == "savings"):
        raise ValueError("savings requires CVRPTW; the other solvers require TSP")
    if provider_name not in ("osrm", "haversine"):
        raise ValueError("provider must be osrm or haversine")
    if solver_name == "held_karp" and len(raw_stops) > 17:
        raise ValueError("live Held–Karp is limited to 17 nodes including the depot")
    horizon = integer(payload.get("shift_end", 28800), "shift_end", 1, 86400)
    vehicle_count = integer(payload.get("vehicles", 1), "vehicles", 1, 6)
    capacity = integer(payload.get("capacity", 25), "capacity", 1, 100000)
    if problem == "TSP" and vehicle_count != 1:
        raise ValueError("TSP uses exactly one vehicle")
    wall_time = integer(payload.get("wall_time_ms", 1000), "wall_time_ms", 1, 2000)
    stops = []
    coords = []
    for index, raw in enumerate(raw_stops):
        if not isinstance(raw, dict) or set(raw) - {"lat", "lon", "demand", "earliest", "latest", "service_time"}:
            raise ValueError(f"stop {index} contains unsupported fields")
        coord = Coord(coordinate(raw.get("lat"), "latitude", 90), coordinate(raw.get("lon"), "longitude", 180))
        demand = integer(raw.get("demand", 1 if problem == "CVRPTW" and index else 0), "demand", 0, 100000)
        service = integer(raw.get("service_time", 120 if problem == "CVRPTW" and index else 0), "service_time", 0, 86400)
        if problem == "TSP" and (demand or service or "earliest" in raw or "latest" in raw):
            raise ValueError("TSP stops cannot carry demand, service time, or windows")
        if index == 0 and (demand or service or "earliest" in raw or "latest" in raw):
            raise ValueError("the depot cannot carry demand, service time, or windows")
        if problem == "CVRPTW" and index:
            earliest = integer(raw.get("earliest", 0), "earliest", 0, 86400)
            latest = integer(raw.get("latest", horizon), "latest", 0, 86400)
            stop = Stop(index, coord=coord, demand=demand, service_time=service, time_window=TimeWindow(earliest, latest))
        else:
            stop = Stop(index, coord=coord)
        coords.append(coord)
        stops.append(stop)

    def provider(unit):
        if provider_name == "osrm":
            return OsrmProvider(base_url=osrm_url, unit=unit, timeout_s=3, dataset_id=dataset_id)
        return HaversineProvider(unit=unit)

    distance_provider = provider(Unit.METRES)
    cost_matrix = distance_provider.build(coords)
    time_matrix = provider(Unit.SECONDS).build(coords)
    vehicles = (Vehicle(0),) if problem == "TSP" else tuple(
        Vehicle(i, capacity=capacity, shift_end=horizon, max_route_duration=horizon)
        for i in range(vehicle_count)
    )
    instance = Instance("live-request", tuple(stops), vehicles, cost_matrix, time_matrix=time_matrix)
    # ponytail: one bounded solve at a time; add worker processes for sustained multi-user load.
    budget = Budget(wall_time_ms=wall_time, max_nodes=10000, max_memory_mb=64)
    return instance, distance_provider, budget


def _solve_prepared(payload, prepared, started):
    instance, distance_provider, budget = prepared
    solver_name, provider_name = payload.get("solver", "nearest_neighbor"), payload.get("provider", "osrm")
    cost_matrix, time_matrix = instance.matrix, instance.time_matrix
    stops, vehicles = instance.stops, instance.vehicles
    coords = [stop.coord for stop in stops]
    solution, report = SOLVERS[solver_name]().solve(instance, budget)
    feasibility = check(instance, solution)
    if report.status.is_feasible and not feasibility.is_feasible:
        raise RuntimeError("solver report disagrees with the independent feasibility check")
    routes = []
    warnings = []
    for route in solution.routes:
        if route.is_empty:
            continue
        nodes = (instance.depot_index, *route.sequence, instance.depot_index)
        geometry = None
        if provider_name == "osrm":
            try:
                geometry = asdict(distance_provider.route_geometry([coords[i] for i in nodes]))
            except OsrmError:
                warnings.append(f"Vehicle {route.vehicle_id}: road geometry is unavailable")
        routes.append({
            "vehicle_id": route.vehicle_id,
            "sequence": list(route.sequence),
            "nodes": list(nodes),
            "cost": route_cost(instance, route),
            "load": sum(stops[i].demand for i in route.sequence),
            "schedule": asdict(schedule(instance, route, vehicles[route.vehicle_id])),
            "geometry": geometry,
        })
    try:
        git = capture_git_state(ROOT)
    except ProvenanceError:
        # Render supplies the checked-out commit to containers without .git.
        revision = os.environ.get("RENDER_GIT_COMMIT", "")
        if (ROOT / ".git").exists() or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise
        git = GitState(revision=revision, dirty=False)
    return {
        "report": asdict(report),
        "headline": report.headline(),
        "feasible": feasibility.is_feasible,
        "violations": [str(v) for v in feasibility.violations],
        "routes": routes,
        "stops": [{"lat": c.x, "lon": c.y} for c in coords],
        "unserved": sorted(solution.unserved),
        "warnings": warnings,
        "matrix": [[cost_matrix[i, j] for j in range(cost_matrix.n)] for i in range(cost_matrix.n)],
        "matrix_metadata": {
            "nodes": cost_matrix.n,
            "unit": cost_matrix.unit.value,
            "symmetric": cost_matrix.is_symmetric,
            "sha256": cost_matrix.content_hash,
        },
        "provenance": {
            "provider": provider_name,
            "provider_fingerprint": distance_provider.cache_fingerprint,
            "geometry_kind": "road" if provider_name == "osrm" else "straight_line_estimate",
            "input_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            "time_matrix_sha256": time_matrix.content_hash,
            "git_revision": git.revision,
            "git_dirty": git.dirty,
            "budget": asdict(budget),
            "pipeline_time_ms": (time.perf_counter() - started) * 1000,
        },
    }


def solve_request(payload, *, osrm_url="http://127.0.0.1:5001", dataset_id=None):
    started = time.perf_counter()
    prepared = _prepare_request(payload, osrm_url=osrm_url, dataset_id=dataset_id)
    return _solve_prepared(payload, prepared, started)


def compare_request(payload, *, osrm_url="http://127.0.0.1:5001", dataset_id=None):
    """Run canonical solvers against one immutable instance, not refetched matrices."""
    if not isinstance(payload, dict):
        raise ValueError("request must be an object containing only supported fields")
    # Validate the submitted algorithm as well, even though comparison selects all methods.
    if not isinstance(payload.get("solver", "nearest_neighbor"), str) or payload.get("solver", "nearest_neighbor") not in SOLVERS:
        raise ValueError("choose a supported problem and solver")
    fleet = payload.get("problem", "TSP") == "CVRPTW"
    if fleet != (payload.get("solver", "nearest_neighbor") == "savings"):
        raise ValueError("savings requires CVRPTW; the other solvers require TSP")
    base = {**payload, "solver": "savings" if fleet else "nearest_neighbor"}
    started = time.perf_counter()
    prepared = _prepare_request(base, osrm_url=osrm_url, dataset_id=dataset_id)
    methods = ["savings"] if fleet else ["nearest_neighbor", "branch_and_bound", "held_karp"]
    skipped = []
    if not fleet and len(prepared[0].stops) > 17:
        methods.remove("held_karp")
        skipped.append({"solver": "held_karp", "reason": "Held–Karp is limited to 17 nodes including the depot in the live app. Reduce the dataset to compare all three; no substitute result was generated."})
    results = [_solve_prepared({**base, "solver": method}, prepared, started) for method in methods]
    return {"results": results, "skipped": skipped}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def allowed_request(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        origins = {f"http://{host}" for host in hosts}
        public_origin = getattr(self.server, "public_origin", None)
        if public_origin:
            hosts.add(urlsplit(public_origin).netloc)
            origins.add(public_origin)
        return self.headers.get("Host") in hosts and (origin is None or origin in origins)

    def send_json(self, value, status=200):
        content = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_HEAD(self):
        if not self.allowed_request():
            self.send_error(403)
        elif self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/live.html")
            self.end_headers()
        elif self.path.split("?", 1)[0] in {"/index.html", "/live.html", "/styles.css", "/app.js", "/live.js", "/route-motion.js", "/route-comparison.js", "/real-data.js", "/evidence.js"}:
            super().do_HEAD()
        else:
            self.send_error(404)

    def do_GET(self):
        if not self.allowed_request():
            self.send_json({"error": "request must use the configured application origin"}, 403)
        elif self.path == "/api/health":
            available = OsrmProvider(base_url=self.server.osrm_url, timeout_s=2).is_available()
            self.send_json({"osrm_available": available, "dataset_id": self.server.dataset_id or "unversioned"})
        elif self.path == "/api/example":
            self.send_json(json.loads((ROOT / "data" / "live" / "monaco.json").read_text()))
        elif self.path == "/api/places/options":
            self.send_json(places_options())
        elif self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/live.html")
            self.end_headers()
        elif self.path.split("?", 1)[0] in {"/index.html", "/live.html", "/styles.css", "/app.js", "/live.js", "/route-motion.js", "/route-comparison.js", "/real-data.js", "/evidence.js"}:
            super().do_GET()
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.allowed_request():
            self.send_json({"error": "request must use the configured application origin"}, 403)
            return
        if self.path not in ("/api/solve", "/api/compare", "/api/places"):
            self.send_json({"error": "not found"}, 404)
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json({"error": "Content-Type must be application/json"}, 415)
            return
        acquired = False
        solve_lock = getattr(self.server, "solve_lock", None)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY_BYTES or self.headers.get("Transfer-Encoding"):
                self.send_json({"error": "request body must be 1–65536 bytes"}, 413)
                return
            payload = json.loads(self.rfile.read(size))
            if self.path in ("/api/solve", "/api/compare") and solve_lock is not None:
                acquired = solve_lock.acquire(blocking=False)
                if not acquired:
                    self.send_json({"error": "Another route is being calculated. Retry shortly."}, 429)
                    return
            if self.path == "/api/places":
                response = fetch_places(payload)
            else:
                operation = compare_request if self.path == "/api/compare" else solve_request
                response = operation(payload, osrm_url=self.server.osrm_url, dataset_id=self.server.dataset_id)
        except (ValueError, TypeError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except OsrmError as exc:
            self.send_json({"error": str(exc)}, 503)
        except PlacesBusy as exc:
            self.send_json({"error": str(exc)}, 429)
        except PlacesError as exc:
            self.log_error("places fetch failed: %r", exc.__cause__ or exc)
            self.send_json({"error": str(exc)}, 503)
        except Exception:
            self.log_error("unexpected solve failure")
            self.send_json({"error": "the solve failed; check the server terminal"}, 500)
        else:
            self.send_json(response)
        finally:
            if acquired:
                solve_lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    parser.add_argument("--public-origin", default=os.environ.get("RENDER_EXTERNAL_URL"))
    parser.add_argument("--osrm-url", default="http://127.0.0.1:5001")
    parser.add_argument("--dataset-id", default=None)
    args = parser.parse_args()
    if args.public_origin:
        parsed = urlsplit(args.public_origin)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            parser.error("public origin must be a single HTTPS application origin")
        args.public_origin = args.public_origin.rstrip("/")
    if args.host == "0.0.0.0" and not args.public_origin:
        parser.error("public serving requires --public-origin or RENDER_EXTERNAL_URL")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.public_origin = args.public_origin
    server.solve_lock = Lock()
    server.osrm_url = args.osrm_url
    server.dataset_id = args.dataset_id
    print(f"Waybill live demo: http://127.0.0.1:{args.port}/live.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
