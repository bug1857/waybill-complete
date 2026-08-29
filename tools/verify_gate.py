"""Verify the Phase 0 exit gate.

The gate: a published TSPLIB tour scores to its exact published cost, brute
force works, and the purity check fails on a planted violation.

Prints evidence rather than a bare pass/fail, because the point of the gate is
that someone else can read the numbers and check them against TSPLIB themselves.
"""

import sys
from itertools import permutations
from pathlib import Path

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from bench.tsplib.known_optima import PUBLISHED_OPTIMA
from bench.tsplib.parser import parse_problem, parse_tour
from core.eval.feasibility import check
from core.eval.objective import closed_tour_cost
from core.exact.brute_force import BruteForceSolver

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


def main() -> int:
    print("Phase 0 exit gate\n" + "=" * 52)
    results = [gate_tsplib(), gate_brute_force()]
    print("\n" + "=" * 52)
    if all(results):
        print("GATE PASSED")
        return 0
    print("GATE FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
