# ADR 0001: Canonical engine and prototype UI boundary

- Status: accepted
- Date: 2026-08-30

## Context

The project has two repositories. `bug1857/waybill` contains the validated Python
foundation and is the implementation under completion. `bug1857/Waybill-G` is a
Google AI Studio prototype with useful visual and interaction ideas, but its routing
logic, fixtures, metrics, and claims are not independently validated.

Combining both repositories wholesale would create two algorithm paths and two sources
of evidence. A polished screen could then display a result that was not produced by the
canonical engine.

## Decision

`bug1857/waybill` is the sole source of truth for:

- problem and solution models;
- distance and travel-time matrices;
- exact and heuristic solvers;
- feasibility checks and solve statuses;
- benchmark inputs, evidence, and report numbers; and
- API response contracts.

The prototype may be consulted only for UI/UX references such as layout, colour,
typography, workflow, map composition, and information hierarchy. Prototype solver
code, benchmark data, result fixtures, and numeric claims must not be copied.

The web demo consumes canonical API responses or a generated canonical evidence
snapshot. It may not calculate routes, invent fallback results, or contain hand-written
performance numbers. Any example mode must identify its evidence bundle and input hash.

## Consequences

- Algorithm changes are made once, in the Python engine.
- The benchmark, generated report, API, and demo share the same serialized result
  contract.
- UI development can proceed independently after the response schema is stable.
- Visual similarity to the prototype is acceptable; evidentiary or algorithmic
  inheritance is not.

## Verification

The completion gate checks that:

1. the web tree contains no routing algorithm implementation;
2. displayed objectives and statuses trace to a canonical response or evidence bundle;
3. no prototype result fixture or hard-coded performance claim is present; and
4. the independent Python feasibility checker validates every surfaced route.
