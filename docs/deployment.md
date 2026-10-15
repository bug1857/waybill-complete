# Free hosted workbench

Deploy the repository's Dockerfile as a Render **Free** web service. No paid
database, disk, worker, custom domain or external routing API is required.
Use the canonical GitHub repository `bug1857/waybill-complete`, branch `main`;
the original repository is retained only as a historical backup.
Render provides `PORT`, `RENDER_EXTERNAL_URL` and `RENDER_GIT_COMMIT`; the server
requires the exact HTTPS origin and records the deployed commit in solve results.

The container contains the canonical Python engine and a private OSRM process
on `127.0.0.1:5000`. A small bundled Jaipur/Monaco extract and the OSRM image
are checksum-pinned and verified during the build. The original regional
sources, extraction recipe and snapshot dates are documented in
`data/roads/README.md`. Only that bounded extract is preprocessed, not India.
Jaipur stop coverage: latitude 26.72–27.13, longitude 75.50–76.02. Monaco's
previous coverage remains unchanged. All road stops must belong to one area;
mixed-area and outside-area road requests fail before reaching OSRM.
Haversine mode remains an explicit geographic estimate (great-circle distance
× 1.3), not a silent road-routing fallback. Road geometry is not live traffic.

Use a **Free** instance and leave automatic deployment off to avoid unnecessary
builds. Free services sleep after inactivity and have monthly usage limits;
this is an academic demo, not an always-on or production availability guarantee.
See [Render's current free-service limits](https://render.com/docs/free).
Do not add a payment method or paid resources for this deployment.

The API allows 100 nodes, six vehicles, a two-second solver budget and one
concurrent solve. Other solves receive HTTP 429; static pages remain responsive.
HTTP Host/Origin checks and bounded bodies are retained. There are no accounts,
server-side persistent storage, GPS tracking, or production dispatch integrations.
Custom stops now have a validated, versioned browser-local draft. Refresh restores
the stop list, not old solve results. Export it before clearing or moving devices;
private browsing, cleared site data or blocked browser storage can lose the draft.

## Optional map context and privacy

The road-coverage diagram separates the larger Jaipur road boundary from the
smaller city-centre public-place query. It does not promise that every point
inside the boundary is reachable on the car network.

Street backgrounds are off by default. Enabling them sends only current viewport
tile requests directly to `https://tile.openstreetmap.org`; browser HTTP caching,
normal Referer/User-Agent headers and visible attribution are retained. There is
no prefetch, offline tile download or tile proxy. Only the active viewport is
requested (at most 48 tiles per view). Keep backgrounds off for confidential
locations. Missing tiles do not change routes, distances or solver proof states.
Mercator display clamps polar latitudes to ±85.0511 degrees; it does not change
the coordinates used by the solver. Public tiles have no availability guarantee.
See the [OSMF tile policy](https://operations.osmfoundation.org/policies/tiles/).

## Automated release checks

GitHub Actions builds the production Docker image, starts it with 512 MiB / one
CPU, and requires OSRM readiness before running all four actual Jaipur/Monaco
integration checks. Playwright then tests Chromium desktop and emulated mobile
journeys: custom draft restore/reorder/export/reset, broken/blocked storage,
coverage boundaries, file import/export, three-way road comparison and graceful
street-tile failures. Public place search uses an explicitly synthetic browser
fixture; tiles are intercepted rather than downloaded by CI. These checks do
not prove public-provider uptime or real-device Safari behavior.

With the image running on loopback port 10000:

```sh
npm ci
npx playwright install chromium
WAYBILL_JAIPUR_API=http://127.0.0.1:10000 python -m pytest -q tests/test_jaipur_integration.py
npm run test:browser
```

Playwright is a pinned development-only dependency. The shipped website and
production image have no new JavaScript runtime dependency.

## Release evidence

Commit the source first. From that clean commit, run `make release-evidence`,
then commit the generated bundle, Markdown results and browser payload together.
The six run manifests identify the clean **source** commit; the later artifact
commit is not misrepresented as the commit used to run the solvers.
Run `python -m tools.verify_gate` after generation. `make gate` is a development
command and intentionally regenerates development evidence.

## Local container check

```sh
docker build -t waybill-release .
docker run --rm -p 127.0.0.1:8003:10000 \
  -e RENDER_EXTERNAL_URL=https://waybill.test \
  -e RENDER_GIT_COMMIT=YOUR_40_CHARACTER_SOURCE_COMMIT waybill-release
curl -H 'Host: waybill.test' http://127.0.0.1:8003/api/health
```

Map data: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
distributed by [Geofabrik](https://download.geofabrik.de/asia/india/northern-zone.html).
