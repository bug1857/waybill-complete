# Canonical Waybill workbench

Run `python -m api.server` from the repository root and open
`http://127.0.0.1:8000/`. All route computation comes from the Python engine.
The static `index.html` reads generated evidence and also works offline.

The previous React/TypeScript implementation is preserved in
`reference/google-ui/` for UI reference and is not part of the deployed app.
See `docs/deployment.md` for the free hosted configuration.

## Real data

**Places & real data → Your own stops** accepts a public place/address search
(include the city) or a name with latitude/longitude. Add each chosen result,
remove unwanted stops, and use **Start here** to choose the depot. **Use these
stops in route planner** loads a closed TSP tour through the 1–99 remaining
stops. Run Solve tour or the algorithm comparison; the list is the input, not a
fixed visit order. Export input retains names and per-place location sources.
Open the HTTP app served by `make live`, rather than double-clicking
`live.html`: file mode disables searches and shows a link to the running app.
Custom trips default to the labelled geographic distance estimate. The existing
Monaco-only road router can be selected for locations within its coverage.

Search uses the [Photon public demo](https://github.com/komoot/photon#demo-server),
with explicit searches, five matches, no key, a 15-second timeout, six-hour
cache, and per-process limits of one new query/second and 100/day. Availability
and map completeness are not guaranteed. The search text is sent to Photon;
manual coordinates stay in the app until the chosen routing provider is used.
No new dependencies are needed.

The **Real data** tab fetches OpenStreetMap places on demand: select a bounded
city-centre area and restaurant/pharmacy/supermarket/hotel category, then
choose a fetched place as depot, customer count and TSP/fleet constraints.
Names, OSM element links, original retrieval time, query and response SHA-256
are retained in the export and the active run's location-source report.
These are mapped locations, not actual customer orders or opening hours.
Fleet parcel demand, service times and shift-wide windows are user assumptions.

Monaco can use the hosted OSRM road extract. Indian areas use the explicitly
labelled geographic distance estimate; they do not have road/traffic coverage.
The fixed HTTPS VK Maps Overpass endpoint rejects redirects. The main
Overpass endpoint was unreachable from the Render host; this documented public
instance is the selected provider, not an automatic retry/failover pool. Queries have a 20-second
upstream timeout, 200-feature cap and 512-KB response limit. Each process caches
results for six hours and allows at most 20 new queries/day, separated by at
least 60 seconds. Cached fetches keep the original timestamp. Upstream errors
never silently produce synthetic places. This is manual academic use, not an
unlimited public business-directory backend; see the
[public-instance usage policy](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances).

Route replay uses cumulative display distance (not one fixed time per stop),
time-based shortest-angle smoothing and a progressive road trace. Its speed
is illustrative, not GPS, traffic or schedule simulation. Playback pauses
when the tab/map is hidden and respects reduced-motion preferences.

Checks: `python -m pytest tests/test_places.py tests/test_live_api.py` and
`node tests/test_route_motion.cjs`; the regular canonical exit gates still apply.

## Algorithm and route comparison

Solver lab automatically compares Greedy, Branch & Bound and Held–Karp on TSP
inputs up to 17 nodes including the depot. Larger inputs retain the first two
runs and show Held–Karp as **not run**, with its size-limit reason; no fake third
tour is supplied. Each solver has the chosen wall-time limit plus a 10,000-state
and 64-MB budget. Exact algorithms may return a feasible incumbent without a
proof. Fleet inputs only run their applicable Clarke–Wright solver.

`POST /api/compare` acquires the distance/time matrices once, shares one immutable
canonical instance across the solvers and independently checks every result.
The route comparison is presentation-only: maps share one geographic projection,
highlight the same visit step or the outgoing edge from a chosen stop, show actual
returned visit orders, and retain the final depot-return leg. Edge costs are read
from the shared matrix. Road geometry is shown only when supplied by OSRM;
offline estimates remain dashed, and missing roads are not replaced by invented
lines. Large datasets hide full tours and non-selected labels by default.
Directed stop-to-stop edge overlap is labelled separately from physical road
coverage. Equal tours and budget-limited results are legitimate outcomes.

Display regression check: `node tests/test_route_comparison.cjs`.

## Import, exports and edited inputs

Import JSON (a stop array or an object containing `stops`) or CSV with two
coordinate columns, optionally four fleet columns. Files are limited to 256 KB
and 2–100 nodes including the depot. JSON exports retain supported model,
algorithm, budget, vehicle and travel settings, plus matching location metadata.
An invalid file leaves the current dataset unchanged. Switching between the
sample and imported dataset restores their settings, not only their coordinates.

Editing inputs marks the displayed route as the previous result, clears stale
audits/comparisons, and disables replay and result/report exports until a fresh
solve completes. A response arriving after an input change is rejected. The
timeline is an elapsed-time schedule, not current traffic or live ETA.

Regression check: `node tests/test_live_ui.cjs`. Browser verification also uses
`tests/fixtures/import-config.json`, `import-valid.csv` and `import-invalid.csv`.
