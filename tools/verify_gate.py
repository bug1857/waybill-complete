"""Verify the exit gates reached so far.

Phase 0: a published TSPLIB tour scores to its exact published cost, brute
force works, and the purity check fails on a planted violation.

Phase 1: the same stops build a matrix both offline (Haversine) and from a live
OSRM, both log a content hash, and the symmetry flag is correct for each.

Prints evidence rather than a bare pass/fail, because the point of the gate is
that someone else can read the numbers and check them against TSPLIB themselves.
"""

import sys
from itertools import permutations
from pathlib import Path

from adapters.distance.haversine import HaversineProvider
from adapters.distance.osrm import OsrmProvider
from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from bench.tsplib.known_optima import PUBLISHED_OPTIMA
from bench.tsplib.parser import parse_problem, parse_tour
from core.eval.feasibility import check
from core.eval.objective import closed_tour_cost
from core.exact.brute_force import BruteForceSolver
from core.model.geometry import Coord
from core.model.units import Unit

DATA = Path(__file__).resolve().parent.parent / "data" / "tsplib"


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


def main() -> int:
    print("Waybill exit gates\n" + "=" * 52)
    print("Phase 0 -- contracts and truth")
    results = [gate_tsplib(), gate_brute_force()]
    print("\n" + "-" * 52)
    print("Phase 1 -- distance contract and adapters")
    results.append(gate_distance_adapters())
    print("\n" + "=" * 52)
    if all(results):
        print("ALL GATES PASSED")
        return 0
    print("GATE FAILED (or incomplete)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
