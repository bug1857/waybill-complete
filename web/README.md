# Canonical Waybill workbench

Run `python -m api.server` from the repository root and open
`http://127.0.0.1:8000/`. All route computation comes from the Python engine.
The static `index.html` reads generated evidence and also works offline.

The previous React/TypeScript implementation is preserved in
`reference/google-ui/` for UI reference and is not part of the deployed app.
See `docs/deployment.md` for the free hosted configuration.

## Real data

The **Real data** tab fetches OpenStreetMap places on demand: select a bounded
city-centre area and restaurant/pharmacy/supermarket/hotel category, then
choose a fetched place as depot, customer count and TSP/fleet constraints.
Names, OSM element links, original retrieval time, query and response SHA-256
are retained in the export and the active run's location-source report.
These are mapped locations, not actual customer orders or opening hours.
Fleet parcel demand, service times and shift-wide windows are user assumptions.

Monaco can use the hosted OSRM road extract. Indian areas use the explicitly
labelled geographic distance estimate; they do not have road/traffic coverage.
The fixed HTTPS Overpass endpoint rejects redirects. Queries have a 20-second
upstream timeout, 200-feature cap and 512-KB response limit. Each process caches
results for six hours and allows at most 20 new queries/day, separated by at
least 60 seconds. Cached fetches keep the original timestamp. Upstream errors
never silently produce synthetic places. This is manual academic use, not an
unlimited public business-directory backend; see the
[provider's fair-use guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html).

Route replay uses cumulative display distance (not one fixed time per stop),
time-based shortest-angle smoothing and a progressive road trace. Its speed
is illustrative, not GPS, traffic or schedule simulation. Playback pauses
when the tab/map is hidden and respects reduced-motion preferences.

Checks: `python -m pytest tests/test_places.py tests/test_live_api.py` and
`node tests/test_route_motion.cjs`; the regular canonical exit gates still apply.
