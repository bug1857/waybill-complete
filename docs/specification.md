# Waybill problem and evidence specification

Status: normative for implementation and experiments  
Version: 1.0

This document turns the architecture plan into executable semantics. When the plan,
README, UI, and code disagree, this specification governs until an explicit architecture
decision changes it.

## 1. Project boundary

Waybill has two related formulations:

1. A TSP kernel used to satisfy the course assignment and establish exact ground truth.
2. A fixed-fleet CVRPTW extension used to demonstrate realistic courier constraints.

The project is an auditable experimental system, not a production dispatch service. It
does not claim live traffic, time-dependent travel, proof of CVRPTW optimality, or
competitive performance with specialist native solvers.

## 2. Shared model

- Nodes are addressed internally by their zero-based position in `Instance.stops`.
- Exactly one node is the depot, identified by `depot_index`.
- Stop IDs are unique display/domain identifiers; algorithms never infer matrix positions
  from arbitrary external IDs.
- Cost and time matrices contain non-negative integers and have a zero diagonal.
- A cost matrix has exactly one unit: metres, seconds, or TSPLIB units.
- A time matrix, when required, is separate and always contains integer seconds.
- A route stores customer indices only. Departure from and return to the depot are
  implicit.

## 3. TSP formulation

Given one depot and a set of customers, find a minimum-cost cycle that:

- starts at the depot;
- visits every customer exactly once;
- returns to the depot.

The objective is the sum of directed matrix entries along that cycle. Symmetry is a
property of a particular matrix, not an assumption of the formulation. A solver may
restrict itself to symmetric instances only if it refuses asymmetric input explicitly.

`PROVEN_OPTIMAL_TSP` is permitted only when an exact algorithm has exhausted its valid
proof condition, the returned tour passes the independent feasibility checker, and the
best global lower bound equals the incumbent objective.

## 4. CVRP and CVRPTW formulation

The fleet is a maximum set of available vehicles; unused vehicles are allowed. Every used
vehicle may drive at most one route.

A complete feasible solution must:

- serve every customer exactly once;
- use no more than one route per vehicle;
- keep each route's integer parcel demand within that vehicle's capacity;
- start no earlier than the vehicle's shift start and return no later than shift end;
- respect any maximum route duration;
- return to the depot;
- start service within each customer's closed hard window;
- include travel, waiting, and service time in its schedule.

Early arrival is allowed and causes waiting. Travel times are static for a run. Breaks,
split deliveries, pickups, multiple depots, and time-dependent traffic are outside the
baseline formulation.

Among complete feasible solutions using the available fleet, the baseline objective is to
minimise total cost in the instance's cost-matrix unit. Vehicle count is reported but is
not a hidden secondary objective. Experiments that use a different or lexicographic
objective must assign it a new configuration identity and state it explicitly.

`Solution.unserved` may preserve a partial incumbent or explain infeasibility. Any
unserved customer makes the solution incomplete; it must not pass the full feasibility
gate or receive feasible wording.

## 5. Result and claim semantics

Feasibility, proof state, termination reason, and external comparison are separate facts.
A rendered headline is derived from those facts and is never authored independently.

- A proven TSP optimum requires a complete feasible tour and a completed proof.
- An exact timeout or node/memory cap may report a complete feasible incumbent and the
  best valid global lower bound. It must never claim optimality.
- A heuristic may report a complete feasible result without a comparator.
- A failed candidate is not evidence that the instance itself is infeasible.
- An external reference always records its name, version/source, objective semantics,
  budget where applicable, and value.

For a minimisation run with incumbent `UB` and lower bound `LB`:

- unresolved fraction normalised by the incumbent is `(UB - LB) / UB`;
- a worst-case relative suboptimality statement uses `(UB - LB) / LB` when `LB > 0`.

Neither quantity may be described more strongly than its denominator permits. A
comparison with a best-known or heuristic reference is a `reference gap`, never an
optimality gap.

A heuristic gap greater than 100% is an anomaly worth investigating, not proof of data
corruption. Correctness comes from input hashes, independent scoring, feasibility, and
appropriate exact/reference comparisons.

## 6. Validation bands

Validation uses overlapping ranges that the algorithms can actually solve:

- independent unreduced enumeration checks the optimised brute-force oracle on tiny
  instances;
- brute force, Held-Karp, and Branch & Bound agree on a seeded small-instance overlap;
- Held-Karp and Branch & Bound agree beyond brute force only while both finish under the
  stated budgets;
- published tours and optima validate supported TSPLIB conventions at their available
  sizes;
- every returned solution passes the independent feasibility checker;
- every Branch & Bound lower bound has a written admissibility argument and is tested on
  every reachable partial state of exhaustive tiny instances, plus randomized cases.

Agreement is supporting evidence, not a substitute for the mathematical validity of a
lower bound.

## 7. Evidence contract

Every empirical result entering a report or demo belongs to a versioned evidence bundle.
Each run records at least:

- evidence schema version and bundle content hash;
- full Git revision and dirty-tree state;
- Python, operating system, architecture, and dependency identity;
- input source and SHA-256;
- full distance-matrix hash and unit;
- solver name/version, complete configuration, seed, and budget;
- termination, feasibility, proof, objective, lower bound, comparator, and instrumentation;
- wall-clock and CPU measurements with the measurement method.

The report and static demo render empirical values from the bundle. Explanatory constants,
formulae, dates, layout dimensions, and citations may remain in source; measured findings
may not.

Evidence generation fails when required provenance is missing. A dirty revision may be
used during development but is displayed prominently and cannot produce a release bundle.

## 8. Reproducibility and data integrity

- Benchmark and road-data inputs are files, not copied arrays in implementation modules.
- Every external input has a source, retrieval date, licence/attribution, and SHA-256.
- Container images are pinned by digest for release evidence.
- An OSRM cache identity includes the routing profile, OSRM build/image, OSM extract hash,
  preprocessing configuration, objective annotation, and coordinate sequence.
- Randomized algorithms use an injected seeded generator. Iteration-count experiments are
  deterministic; wall-clock performance experiments are explicitly not assumed to have
  identical traces.
- Counterexamples discovered by generated tests become named regression fixtures.

## 9. Completion gates

The project is complete when a clean checkout can:

1. install and import a built wheel;
2. run the hermetic test suite and optional OSRM integration suite;
3. reproduce supported published TSPLIB tour costs;
4. demonstrate exact-solver agreement and lower-bound validity in realistic bands;
5. generate a versioned evidence bundle, tables, figures, and report with one documented
   command;
6. produce a complete feasible 150-stop, six-vehicle CVRPTW plan on a named reproducible
   instance or honestly report why that named instance is infeasible;
7. open a static evidence demo without a solver process, with optional live solving kept
   behind a resource-limited API;
8. trace every displayed empirical number back to one bundle run and its manifest.

