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

**Phases 0, 1 and 2 complete — all exit gates passed.** Phase 3 (the Branch &
Bound bound-quality experiment) is next.

**The assignment's three named techniques — TSP, Greedy, and Branch & Bound — are
implemented and validated as of Phase 2.**

```
make setup          # create .venv, install dev deps
make test           # 262 tests
make gate           # verify every exit gate reached so far
make crosscheck     # Python and TypeScript engines must agree
make web-dev        # run the interface
make osrm-prepare   # one-off: preprocess the OSM extract
make osrm-up        # start the local routing server
```

### Phase 0 — contracts and truth

Model layer, TSPLIB conventions, the independent feasibility checker, the
`SolveStatus`/`SolveReport` contract, the `Solver` protocol, brute-force
enumeration, and the core purity checker. Five coordinate instances score their
published optima exactly (eil51 426, berlin52 7542, st70 675, pr76 108159,
kroA100 21282).

### Phase 1 — distance contract and adapters

Haversine, a self-hosted OSRM client, and a SQLite cache — all in `adapters/`,
never in `core/`. On five real Monaco stops, **all 10 coordinate pairs differ by
direction**, largest gap 130 s (296 s one way, 426 s back).

| Provider | Symmetric | Matrix hash |
|---|:--:|---|
| `haversine` | true | `587a429c5c88b7d6` |
| `osrm` | **false** | `b04816a09b5f83ce` |

### Phase 2 — assignment-complete solver core

Nearest neighbour, Clarke–Wright savings, Held–Karp DP, and Branch & Bound with
the reduced-cost bound, plus TSPLIB `EXPLICIT` matrix parsing.

**Three independent exact solvers agree** across 72 seeded instances, symmetric
and asymmetric, and the lower bound never exceeded a true optimum in 60 checks.

`EXPLICIT` instances are matrix-defined; their coordinates are `DISPLAY_DATA` and
are never used as geometry. All three row formats verified against published
optima:

| Instance | Format | Computed | Published |
|---|---|---:|---:|
| bayg29 | `UPPER_ROW` | 1610 | 1610 |
| bays29 | `FULL_MATRIX` | 2020 | 2020 |
| gr24 | `LOWER_DIAG_ROW` | 1272 | 1272 |

`gr17` (n=17, `LOWER_DIAG_ROW`) is solved to **2085 — the published optimum —
proven optimal by Held–Karp in about 1 s**, validating the explicit parser and
the dynamic program against one external number simultaneously.

#### Measured crossover, arm64 / Python 3.14, seed 1

| n | optimum | brute force | Held–Karp | B&B | B&B explored | B&B pruned |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 3449 | 220 ms | 3 ms | 8 ms | 257 | 942 |
| 11 | 3487 | 2.32 s | 8 ms | 13 ms | 253 | 1,133 |
| 12 | 3627 | refused | 16 ms | 34 ms | 570 | 2,825 |
| 14 | 3801 | refused | 81 ms | 478 ms | 6,321 | 36,548 |

Brute force becomes unusable at n≈11. **Held–Karp is faster than Branch & Bound
throughout this range** — B&B's advantage is memory, not speed, and Held–Karp
dies on its table (about 800 MB at n=21) rather than on time. Single-seed gap
figures move around by more than ten points between adjacent sizes, which is why
Phase 4 requires ≥30 seeds with bootstrap intervals rather than a single run.

The full architecture and build plan is in [`docs/architecture-plan.pdf`](docs/architecture-plan.pdf)
(revision 3, 22 pages). Earlier revisions are in `docs/archive/`; the current document opens
with a changelog of what changed and why.

Revision 3 adds the **evidence bundle**: `bench/` emits a single `evidence.json` carrying every
measured result plus its manifest, and both the report and the demo render from that file and
nothing else. Neither can state a number the engine did not produce. A build step fails on any
numeric literal in `report/` or `web/`. It also adds §05 data-integrity rules — no numeric
instance data may be typed into source, every input file is checksummed — and §13, a named list
of claims this project will not make.

### Regenerating the plan PDF

`docs/plan/waybill.html` is the source of truth. Rendering it to PDF needs a
Chromium-family browser and Python 3; see the plan document itself for the print setup.
The published web version is theme-aware and carries the same content.
