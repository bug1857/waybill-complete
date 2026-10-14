# Waybill

Use [bug1857/waybill-complete](https://github.com/bug1857/waybill-complete),
branch **main**, as the canonical repository for all further work. The original
`waybill` repository is a historical backup; the Google prototype remains a UI
reference, not a second solver implementation to deploy.
[Open the complete website](https://waybill-17fd.onrender.com/live.html).

Project topic: **Courier Delivery Route Optimization System** (High level).
Required DAA concepts: **TSP, Greedy, Branch & Bound**.

Waybill's primary demo solves a single courier's closed TSP tour and compares
Greedy nearest neighbour, admissible-bound Branch & Bound, and Held–Karp on the same input
and matrix. It shows measured distance, runtime, explored/pruned nodes, lower
bound, feasibility, and stop reason. Optimality is claimed only for a completed
proof. Held–Karp is a cross-check run automatically up to 17 nodes; constrained CVRPTW fleet
routing is an extension. The canonical Python engine is the source of truth;
the static UI renders generated evidence and contains no routing logic.

## What is implemented

- Exact TSP: brute force, Held–Karp, and admissible-bound Branch & Bound.
- Heuristic TSP: deterministic nearest neighbour, symmetry-guarded 2-opt,
  asymmetric-safe Or-opt, and seeded simulated annealing.
- CVRPTW: directed Clarke–Wright construction with hard capacity, service,
  time-window, shift, return, and one-route-per-vehicle checks.
- Reproducible evidence: signed-input manifests, content-hashed evidence JSON,
  generated Markdown report, and a static evidence viewer.

Claims are typed. A heuristic plan is feasible, not optimal; a partial run is
not an infeasibility proof; and a reference comparison is not an optimality
certificate.

## Run it

```sh
make setup
make gate
open web/index.html
```

`make gate` is hermetic. It runs purity checks, regenerates the evidence bundle
and report, validates exact-solver agreement, checks the named 150-customer /
six-vehicle CVRPTW plan, and validates the generated report. Outputs are:

- [`artifacts/evidence.json`](artifacts/evidence.json)
- [`report/results.md`](report/results.md)
- [`web/index.html`](web/index.html)

The bundle records the current Git revision and dirty state. Regenerate it from
a clean commit for release evidence.

## Optional real-road integration

OSRM is deliberately separate from the hermetic gate:

```sh
make osrm-prepare
make osrm-up
make osrm-gate
```

This verifies the Haversine and local OSRM adapters on the same stops. The
static demo remains usable without Docker or a running service.

## Live API and route map

Run `make live`, then open `http://127.0.0.1:8000/`. The integrated workbench
includes dispatch, solver comparison, directed-matrix analysis, generated
evidence, runtime invariants, import/export, and printable reports. The map draws
OSRM road geometry and schedules use the same travel-time matrix as the solver.
An offline distance estimate is also available.
**Places & real data → Your own stops** supports public place search or manual
coordinates. Choose a start/return depot, add delivery destinations, then send
the dataset to the same canonical solver. Location names and source metadata
survive export/import. Custom trips inside one bundled Jaipur or Monaco area
default to road routing. Outside those areas they use labelled geographic
estimates (great-circle distance × 1.3), not driving distances or live traffic.
The Route planner opens in TSP mode. Use **Compare all algorithms & routes**
to run the required topic comparison, then view any returned tour without
re-solving it. The Project & report tab explains the formulation and algorithms
and includes the measured comparison when it belongs to the active result.
To use the current alternate local port: `.venv/bin/python -m api.server --port 8001`.

The route explorer replays the returned tour with play/pause, next-stop, speed,
and scrub controls. OSRM playback uses per-leg road geometry; offline playback
is explicitly a straight-line estimate. This is illustrative replay, not live
GPS or an ETA simulation. Inputs over 30 nodes default to a focused current-leg
view with fewer labels; full routes, stop inspection, zoom/pan and the underlying
schedules remain available. Reduced-motion users can step or scrub without
continuous animation. Playback pauses off-screen and on tab changes.
Run `node tests/test_route_motion.cjs`, `node tests/test_route_comparison.cjs`,
and `node tests/test_live_ui.cjs` for motion, comparison, import and stale-result checks.

The local API accepts `POST /api/solve` and returns the canonical `SolveReport`,
independent feasibility results, route geometry, schedules, and input/matrix
hashes. It allows up to 100 nodes, six vehicles, and a two-second solver budget.
Held–Karp is limited to 17 nodes. The service binds to loopback by default and
allows one bounded solve at a time. Road matrix and geometry requests have separate network
timeouts; the solver budget does not include their elapsed time.

For dataset provenance, run `python -m api.server --dataset-id <extract/build-identity>`.
Without this argument, the OSRM dataset is explicitly labelled unversioned.

## Hosted release

The [free deployment guide](docs/deployment.md) describes the complete Docker
workbench with its own pinned Jaipur/Monaco road router and clean-source release evidence.
The Python wheel is for engine/library use. The complete website runs from the
source checkout or Docker image, which also supplies web assets and datasets.
The preserved Google UI prototype is in `reference/google-ui`; it is not the
deployed computation path.

## Scope

The named fleet scenario is a reproducible synthetic integration fixture, not
a claim about live traffic or production dispatch. The Google AI Studio
prototype informed the visual hierarchy only; no prototype solver, data, or
metric is used. See
[`docs/decisions/0001-canonical-engine-and-ui-boundary.md`](docs/decisions/0001-canonical-engine-and-ui-boundary.md).
