# Release validation · 13 October 2026

The initial polish retained the canonical engine and repaired routing, input
handling and presentation. The later combined release also integrates custom
place search/manual stops. No new runtime dependency is introduced.

## Initial polish: verified locally

- 780 Python tests passed with the existing Docker OSRM router online; none
  skipped. All three Node checks passed: motion, route comparison and live UI.
- Core purity passed for 33 modules; 20 benchmark input SHA-256 manifests
  verified. All acceptance gates passed, including live asymmetric road
  matrices, exact-solver agreement and the 150-customer/six-vehicle fleet.
- The full Docker image built and started with the pinned Monaco extract.
  A 100-node road solve served all 99 customers, returned road geometry and
  scored 25,744 metres. The cost was independently recomputed from its matrix.
  These input coordinates are a synthetic stress fixture, not real orders.
- The Python wheel built and installed into a separate environment outside the
  checkout. Imports, independent feasibility and exact-solver agreement passed.
  The wheel is an engine/library package; the complete website uses the source
  checkout or Docker image with assets and datasets.
- Native browser JSON import restored Held–Karp, 250 ms and Haversine settings.
  Input export/re-import and sample/custom switching retained settings; a
  named test dataset also retained aligned location names and source metadata.
  Valid CSV imported; invalid CSV left the previous dataset untouched.
- Actual input JSON, canonical result JSON and Markdown report downloads were
  parsed and checked. Browser invariants passed. Replay stepping, restart and
  animated completion were exercised; 100 nodes defaulted to a focused leg
  with full-route and all-label overlays off.
- Three TSP comparison maps rendered from returned tours. At 390px there was
  no page-wide horizontal overflow; the wide ledger remained locally scrollable.
  At 1000px the single fleet comparison map filled its 937px available width.

## Fixes and boundaries

Pinned Monaco routing now rejects out-of-area input before network calls;
Jaipur road requests return an actionable HTTP 400, not a zero-metre tour.
Geographic estimates remain explicitly available elsewhere. Malformed,
oversized and timed-out OSRM responses are typed errors. Imports are validated
before replacing input; changed inputs reject late responses and disable stale
result exports/replay. Reports identify the last calculated plan when edited.

The public VK Maps Overpass request returned HTTP 504 during this validation.
The browser showed the upstream error without fabricating places or replacing
the current input. Fresh successful POI retrieval was therefore not verified
in that local check; source-preservation behavior was exercised with labelled fixtures.
Public provider availability is not guaranteed and is not part of solver proof.

Print-dialog output, live GPS/traffic and production dispatch were not tested
or claimed. Render Free may sleep and has quotas. Exact methods can exhaust
their budgets; only `PROVEN_OPTIMAL_TSP` establishes optimality for that input.
Release evidence must be regenerated from a clean committed source, followed
by verification of the deployed commit and CI in the pull request.

## Combined custom-place release

`bug1857/waybill-complete`, branch `main`, is the canonical repository.
The older repositories/local checkouts are retained as backups and references.
The other chat's completed custom-place work is included, not omitted.

- 791 Python tests passed with Docker online; none skipped. All three Node
  suites, core purity, benchmark manifests and the OSRM acceptance gate passed.
- A genuine Photon search for Hawa Mahal in Jaipur returned mapped results.
  Browser checks covered adding a result, rejecting a duplicate, manual depot
  entry, choosing start/return, removal, canonical comparison and export/import.
  The named regression depot is synthetic test input, not a customer order.
- The custom two-node estimate tour scored 10,730 metres. All three algorithms
  covered its one customer; exact methods completed a proof on that input.
  Names, manual/search source labels, query and response hash survived import.
- Unicode metadata for 100 custom locations can exceed the old 64-KB import
  cap. Imports now accept at most 256 KB, with size checked before reading.
  The solve API still has its independent 64-KB body limit and 100-node cap.
- File mode makes no data requests, disables unsupported search/routing, and
  links to the HTTP app. Photon is an explicit bounded search provider;
  availability and mapped-location accuracy are not guaranteed.

The current generated solver bundle identifies clean source
`ee4a85419e60e1858d78b271aabc81e491c59196`, separately from the later
artifact/merge commit. Hosted verification and merge status are recorded in PR #1.
