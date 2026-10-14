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
persistent storage, GPS tracking, or production dispatch integrations.

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
