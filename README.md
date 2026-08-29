# Waybill

A courier delivery route optimization engine — and an experiment measuring when exact
optimization stops being worth its cost.

**Course:** Design & Analysis of Algorithms · Project 4 (TSP, Greedy, Branch & Bound)

---

## The thesis

The assignment asks for TSP. **Couriers do not solve TSP.**

TSP is one vehicle, unlimited capacity, no clock, symmetric distances. A real fleet has
multiple vans with capacity limits, customers with delivery time windows, service time at
each door, driver shift limits, and asymmetric road distances — because one-way streets
mean `d(A,B) ≠ d(B,A)`.

The correct problem is **CVRPTW** (Capacitated Vehicle Routing with Time Windows). TSP is
the kernel inside it.

So this project does both: it satisfies the assignment exactly — TSP with Greedy and
Branch & Bound — then extends to the real formulation and measures the difference.

## What makes it more than an implementation

Implementing algorithms is not a result. **Measuring them against a proven optimum is.**

- Exact solvers (brute force, Held–Karp, Branch & Bound) establish ground truth where
  proof is computationally possible.
- Heuristics (nearest neighbour, Clarke–Wright savings, Or-opt/2-opt, simulated
  annealing) scale indefinitely with unknown quality.
- The experiment measures the gap between them, and locates the crossover where exact
  methods stop being practical.

**Primary research question:** at what problem size and compute budget does exact
optimization stop being worth its cost, and how much solution quality is given up by
switching to scalable heuristics?

## Claim discipline

Every solve returns a typed status, and no part of the system may word a result more
strongly than its status permits:

| Status | Permitted wording |
|---|---|
| `PROVEN_OPTIMAL_TSP` | "Optimal" — for that TSP instance only |
| `EXACT_TIMEOUT_WITH_INCUMBENT` | Report incumbent **and** lower bound. Never "optimal" |
| `HEURISTIC_FEASIBLE_CVRPTW` | "Feasible." Quality only relative to a named comparator |
| `HEURISTIC_INFEASIBLE` | Reject. Never surface as a route |
| `REFERENCE_GAP_ONLY` | "Gap to reference" — never "optimality gap" |

"Optimality gap" is only meaningful when the denominator is a proven optimum or a valid
bound. Against TSPLIB published optima it is legitimate; against OR-Tools it is not.

## Architecture

One rule governs the layout: **`core/` imports nothing that touches a socket, a disk, or
a database.** It holds the algorithms and the protocols; every I/O implementation lives in
`adapters/`. A test walks `core/`'s import graph and fails the build if that rule is
broken, so it cannot drift.

```
core/        pure algorithms + protocols (stdlib only, enforced by test)
adapters/    OSRM client, distance cache, persistence — all real I/O
bench/       experiment runner, manifests, plots, OR-Tools reference
api/         thin FastAPI orchestration — no algorithm logic
web/         React + MapLibre
infra/       docker compose: OSRM, Postgres, Redis
report/      generated tables, figures, written analysis
```

Because `bench/` and `api/` import the same solver code, a benchmark number is a claim
about the deployed system — not about a separate "benchmark version."

## Validation chain

No problem size goes unchecked, and the bands overlap at their boundaries:

| Range | Check |
|---|---|
| n ≤ 12 | Brute force — the root of trust |
| 13 – 51 | Mutual agreement: brute force ≡ Held–Karp ≡ B&B, sharing no code path |
| n ≥ 52 | TSPLIB published optima — external ground truth |
| all sizes | Independent feasibility checker on every solution |
| all bounds | **Lower bound ≤ true optimum** on every brute-force-verifiable instance |

That last invariant is the most important test in the project. An invalid lower bound does
not crash — it silently prunes the optimum and reports `PROVEN_OPTIMAL`. It is the only
thing standing between the solver and a confidently wrong answer.

## Build phases

Each phase has an exit gate — a falsifiable condition, not a description of intent.

| Phase | Focus | Exit gate |
|---|---|---|
| 0 | Contracts and truth | TSPLIB tour scores to its published cost; purity test catches a planted import |
| 1 | Distance contract + adapters | Same instance runs offline and on OSRM; both log a matrix hash |
| 2 | Assignment-complete solver core | All three exact solvers agree across a seeded suite |
| 3 | The B&B experiment | Bound-comparison plot generates from raw data; validity invariant passes |
| 4 | Heuristic quality ladder | Gap-vs-n and anytime curves reproduce from one command |
| 5 | CVRPTW constraints | 150 stops / 6 vehicles passes the independent checker |
| 6 | Evidence freeze | Every report number regenerates in a clean environment |
| 7 | API + map | Demo reads real `SolveReport` fields; no duplicated algorithm logic |
| 8 | Stretch | Attempted only if Phase 6 is complete and stable |

**Effort split:** 70% core and benchmark evidence · 20% real-road and CVRPTW integration ·
10% API and interface. A polished interface cannot compensate for an unvalidated exact
solver.

Phases 0–2 satisfy the assignment's stated requirements in full.

## Ground rules

- **Integer seconds and integer metres internally.** Float comparison in feasibility
  checks produces bugs you will not find.
- **OR-Tools is a ruler, never an engine.** It lives in `bench/` as a reference baseline
  and never inside a submitted solver.
- **Textbook 2-opt is invalid on asymmetric matrices.** The segment reversal that makes
  its `O(1)` delta work depends on `d(x,y) = d(y,x)`. Under real road data it optimizes a
  quantity that is not the tour length — without erroring. Or-opt and relocate are the
  asymmetry-safe operators; 2-opt carries a symmetry guard.
- **No number goes in the report before it is measured.** The write-up template has blanks,
  not placeholders borrowed from the literature.

## Status

**Phases 0 and 1 complete — both exit gates passed.** Phase 2 (assignment-complete
solver core) is next.

```
make setup          # create .venv, install dev deps
make test           # 186 tests (179 without Docker)
make gate           # verify every exit gate reached so far
make osrm-prepare   # one-off: preprocess the OSM extract (~1 min for Monaco)
make osrm-up        # start the local routing server
```

### Phase 0 — contracts and truth

The pure model layer (`Instance`, `Solution`, `Stop`, `TimeWindow`, `Vehicle`,
`DistanceMatrix`), TSPLIB distance conventions, the independent feasibility checker,
the `SolveStatus`/`SolveReport` contract, the `Solver` protocol, brute-force
enumeration, and the core purity checker.

Our own distance implementation scoring the published optimal tours:

| Instance | n | Computed | Published | Match |
|---|---:|---:|---:|:--:|
| eil51    |  51 |    426 |    426 | ✓ |
| berlin52 |  52 |   7542 |   7542 | ✓ |
| st70     |  70 |    675 |    675 | ✓ |
| pr76     |  76 | 108159 | 108159 | ✓ |
| kroA100  | 100 |  21282 |  21282 | ✓ |

Brute force also agrees with unreduced permutation enumeration on 60 random instances
(30 symmetric, 30 asymmetric), and `tools/check_purity.py` fails the build on a planted
`import requests` inside `core/`.

### Phase 1 — distance contract and adapters

`DistanceProvider` implementations live in `adapters/`, never in `core/`: Haversine for
offline and hermetic tests, a self-hosted OSRM client for real road data, and a SQLite
cache that wraps either. `infra/` carries the Docker pipeline and a pinned OSM extract,
so matrices are reproducible rather than dependent on a public server's current data.

Same five Monaco stops, two providers:

| Provider | Symmetric | Matrix hash |
|---|:--:|---|
| `haversine` | **true** | `587a429c5c88b7d6` |
| `osrm` | **false** | `b04816a09b5f83ce` |

All 10 coordinate pairs differ by direction under real road data; the largest gap is
**130 s** (296 s one way, 426 s back). That asymmetry is not a curiosity — it is what
invalidates textbook 2-opt, and Phase 4 has to handle it.

The full architecture and build plan is in [`docs/architecture-plan.pdf`](docs/architecture-plan.pdf)
(24 pages). Revision 1 is kept in `docs/archive/` for reference; the current document opens
with a changelog of what changed between them and why.

### Regenerating the plan PDF

`docs/plan/waybill.html` is the source of truth. Rendering it to PDF needs a
Chromium-family browser and Python 3; see the plan document itself for the print setup.
The published web version is theme-aware and carries the same content.
