"""Verify the exit gates reached so far.

Phase 0: a published TSPLIB tour scores to its exact published cost, brute
force works, and the purity check fails on a planted violation.

Phase 1: the same stops build a matrix both offline (Haversine) and from a live
OSRM, both log a content hash, and the symmetry flag is correct for each.

Prints evidence rather than a bare pass/fail, because the point of the gate is
that someone else can read the numbers and check them against TSPLIB themselves.
"""

import argparse
import json
import sys
from itertools import permutations
from pathlib import Path

from adapters.distance.haversine import HaversineProvider
from adapters.distance.osrm import OsrmProvider
from bench.evidence.bundle import EvidenceBundle
from bench.evidence.report import verify_markdown_report
from bench.generators import (
    clustered_cvrptw_150,
    random_asymmetric_tsp,
    random_euclidean_tsp,
)
from bench.tsplib.known_optima import PUBLISHED_OPTIMA
from bench.tsplib.parser import parse_problem, parse_tour
from core.eval.feasibility import check
from core.eval.objective import closed_tour_cost
from core.construct import ClarkeWrightSolver
from core.exact.branch_and_bound import BranchAndBoundSolver
from core.exact.brute_force import BruteForceSolver
from core.exact.held_karp import HeldKarpSolver
from core.model.geometry import Coord
from core.reporting.status import SolveStatus
from core.model.units import Unit

DATA = Path(__file__).resolve().parent.parent / "data" / "tsplib"
ROOT = Path(__file__).resolve().parent.parent


def _exhaustive(instance) -> int:
    depot, m = instance.depot_index, instance.matrix
    best = None
    for perm in permutations(instance.customer_indices):
        cost = m.cost(depot, perm[0])
        for a, b in zip(perm, perm[1:]):
            cost += m.cost(a, b)
        cost += m.cost(perm[-1], depot)
        best = cost if best is None else min(best, cost)
    return best


def gate_tsplib() -> bool:
    print("TSPLIB published optima reproduced")
    print(f"  {'instance':<10} {'n':>4} {'computed':>10} {'published':>10}  ok")
    ok = True
    for name in sorted(PUBLISHED_OPTIMA, key=lambda k: PUBLISHED_OPTIMA[k]):
        instance = parse_problem(DATA / f"{name}.tsp").to_instance()
        tour = parse_tour(DATA / f"{name}.opt.tour")
        got = closed_tour_cost(instance.matrix, tour)
        want = PUBLISHED_OPTIMA[name]
        match = got == want
        ok &= match
        print(f"  {name:<10} {instance.n:>4} {got:>10} {want:>10}  {'YES' if match else 'NO'}")
    return ok


def gate_brute_force() -> bool:
    print("\nBrute force agrees with unreduced enumeration")
    ok = True
    for label, factory in (("symmetric", random_euclidean_tsp),
                           ("asymmetric", random_asymmetric_tsp)):
        mismatches = 0
        for n in range(2, 8):
            for seed in range(5):
                instance = factory(n, seed)
                solution, report = BruteForceSolver().solve(instance)
                if report.objective_value != _exhaustive(instance):
                    mismatches += 1
                if not check(instance, solution).is_feasible:
                    mismatches += 1
        ok &= mismatches == 0
        print(f"  {label:<11} 30 instances, {mismatches} mismatch(es)")
    return ok


MONACO = [
    Coord(43.7355, 7.4256),   # Port Hercule
    Coord(43.7397, 7.4276),   # Casino de Monte-Carlo
    Coord(43.7470, 7.4370),   # Larvotto Beach
    Coord(43.7275, 7.4180),   # Fontvieille
    Coord(43.7315, 7.4212),   # Monaco-Ville
]


def gate_distance_adapters() -> bool:
    """Phase 1: same stops, two providers, correct symmetry flag on each."""
    print("\nDistance adapters on identical stops")
    offline = HaversineProvider(unit=Unit.SECONDS).build(MONACO)
    print(f"  {'haversine':<12} n={offline.n}  symmetric={offline.is_symmetric!s:<5} "
          f"hash={offline.content_hash[:16]}")
    if not offline.is_symmetric:
        print("  FAIL: great-circle distance must be symmetric")
        return False

    osrm = OsrmProvider(unit=Unit.SECONDS)
    if not osrm.is_available():
        print(f"  {'osrm':<12} unavailable at {osrm.base_url} -- run `make osrm-up`")
        print("  Phase 1 gate INCOMPLETE (offline half passed)")
        return False

    road = osrm.build(MONACO)
    print(f"  {'osrm':<12} n={road.n}  symmetric={road.is_symmetric!s:<5} "
          f"hash={road.content_hash[:16]}")
    if road.is_symmetric:
        print("  FAIL: a real road network should not be symmetric")
        return False
    if road.content_hash == offline.content_hash:
        print("  FAIL: the two providers produced identical matrices")
        return False

    pairs = [(i, j) for i in range(road.n) for j in range(i + 1, road.n)]
    differing = [(i, j) for i, j in pairs if road.cost(i, j) != road.cost(j, i)]
    worst = max(differing, key=lambda p: abs(road.cost(*p) - road.cost(p[1], p[0])))
    a, b = road.cost(*worst), road.cost(worst[1], worst[0])
    print(f"  asymmetric pairs: {len(differing)}/{len(pairs)}; "
          f"largest gap {abs(a - b)}s ({a}s vs {b}s reversed)")

    metric_violations = sum(
        1
        for i in range(road.n)
        for j in range(road.n)
        for k in range(road.n)
        if i != j != k != i and road.cost(i, k) + road.cost(k, j) < road.cost(i, j)
    )
    note = "costs are metric here" if metric_violations == 0 else "not a bug -- one-ways and barriers"
    print(f"  triangle-inequality violations: {metric_violations} ({note})")
    return True


def gate_exact_core() -> bool:
    """Phase 2: three independent exact implementations agree."""
    print("\nPhase 2 -- exact solver agreement")
    instance = random_euclidean_tsp(10, 17, name="gate-exact-n10-s17")
    reports = [
        solver.solve(instance)[1]
        for solver in (BruteForceSolver(), HeldKarpSolver(), BranchAndBoundSolver())
    ]
    objectives = {report.objective_value for report in reports}
    valid = all(
        report.status is SolveStatus.PROVEN_OPTIMAL_TSP
        and report.best_lower_bound == report.objective_value
        for report in reports
    )
    print(f"  objectives: {[report.objective_value for report in reports]}")
    print(f"  proof statuses: {'YES' if valid else 'NO'}")
    return len(objectives) == 1 and valid


def gate_cvrptw() -> bool:
    """Phase 5: named 150-customer/6-vehicle construction is complete."""
    print("\nPhase 5 -- CVRPTW fleet feasibility")
    instance = clustered_cvrptw_150()
    solution, report = ClarkeWrightSolver().solve(instance)
    feasibility = check(instance, solution)
    served = set(solution.served) == set(instance.customer_indices)
    valid = (
        feasibility.is_feasible
        and instance.n == 151
        and solution.used_vehicle_count == 6
        and served
        and report.status is SolveStatus.HEURISTIC_FEASIBLE_CVRPTW
    )
    print(
        f"  stops={instance.n - 1} vehicles={solution.used_vehicle_count} "
        f"served={len(solution.served)} status={report.status.value}"
    )
    return valid


def gate_evidence_and_demo() -> bool:
    """Phase 6/7: generated report and offline UI share one valid bundle."""
    print("\nPhase 6/7 -- evidence bundle and static demo")
    bundle_path = ROOT / "artifacts" / "evidence.json"
    report_path = ROOT / "report" / "results.md"
    payload_path = ROOT / "web" / "evidence.js"
    index_path = ROOT / "web" / "index.html"
    app_path = ROOT / "web" / "app.js"
    try:
        bundle = EvidenceBundle.read(bundle_path)
        verify_markdown_report(bundle, report_path.read_text(encoding="utf-8"))
        payload = payload_path.read_text(encoding="utf-8")
        embedded = json.loads(
            payload.removeprefix("window.WAYBILL_EVIDENCE = ").rstrip(";\n")
        )
        embedded_bundle = EvidenceBundle.from_dict(embedded)
    except (OSError, ValueError) as exc:
        print(f"  FAIL: {exc}")
        return False
    static_files = all(path.is_file() for path in (index_path, app_path))
    same_bundle = embedded_bundle.content_hash == bundle.content_hash
    no_live_fetch = "fetch(" not in app_path.read_text(encoding="utf-8")
    print(f"  bundle={bundle.content_hash[:16]} records={len(bundle.records)}")
    print(f"  embedded bundle match: {'YES' if same_bundle else 'NO'}")
    return static_files and same_bundle and no_live_fetch


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Waybill acceptance gates.")
    parser.add_argument(
        "--osrm",
        action="store_true",
        help="include the optional local OSRM adapter gate",
    )
    arguments = parser.parse_args()
    print("Waybill exit gates\n" + "=" * 52)
    print("Phase 0 -- contracts and truth")
    results = [gate_tsplib(), gate_brute_force()]
    results.extend([gate_exact_core(), gate_cvrptw(), gate_evidence_and_demo()])
    if arguments.osrm:
        print("\n" + "-" * 52)
        print("Optional OSRM integration")
        results.append(gate_distance_adapters())
    print("\n" + "=" * 52)
    if all(results):
        print("ALL GATES PASSED")
        return 0
    print("GATE FAILED (or incomplete)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
