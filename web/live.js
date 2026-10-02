(function () {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const form = byId("solve-form");
  const routeColours = ["#2f7ed8", "#1f9d73", "#f59e0b", "#d9468f", "#7c3aed", "#0891b2"];
  let currentResult = null;
  let currentPayload = null;
  let datasetName = "Monaco harbour deliveries";
  let comparison = null;
  let sampleInput = "";
  let importedInput = "";
  let importedName = "";
  const motion = window.WaybillMotion;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let playback = null;
  let selectedStop = 0;
  let mapView = [0, 0, 900, 550];
  let mapPositions = new Map();
  const solverLabel = (name) => ({ nearest_neighbor: "Greedy · nearest neighbour", branch_and_bound_min_in_out: "Branch & Bound", held_karp: "Held–Karp", clarke_wright_savings: "Clarke–Wright" }[name] || name);

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  async function request(path, options) {
    const response = await fetch(path, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  function setBusy(button, busy, busyLabel, normalLabel) {
    button.disabled = busy;
    button.textContent = busy ? busyLabel : normalLabel;
  }

  function chooseModel() {
    const fleet = byId("problem").value === "CVRPTW";
    byId("fleet-fields").hidden = !fleet;
    byId("hero-type").textContent = fleet ? "CVRPTW formulation" : "TSP formulation";
    byId("instance-type").textContent = fleet ? "CVRPTW" : "TSP";
    byId("solve-button").textContent = fleet ? "Dispatch fleet" : "Solve tour";
    byId("compare-topic").textContent = fleet ? "Inspect fleet solver" : "Compare Greedy vs Branch & Bound";
    byId("comparison-scope").textContent = fleet ? "Fleet extension selected. Only Clarke–Wright applies; select TSP in Route planner for the project comparison." : "Primary comparison: Greedy and Branch & Bound. Held–Karp is an optional validation method.";
    const selected = byId("solver").value;
    byId("solver").replaceChildren();
    const options = fleet ? [["savings", "Clarke–Wright savings"]] : [
      ["nearest_neighbor", "Greedy · nearest neighbour"], ["branch_and_bound", "Branch & Bound"], ["held_karp", "Held–Karp · optional cross-check"],
    ];
    for (const [value, label] of options) {
      const option = element("option", label); option.value = value; option.selected = value === selected; byId("solver").append(option);
    }
  }

  function parseStops() {
    const source = byId("stops").value.trim();
    if (!source) throw new Error("Enter at least a depot and one stop.");
    return source.split(/\n+/).map((line, index) => {
      const pieces = line.split(",").map((part) => part.trim());
      if (![2, 6].includes(pieces.length) || pieces.some((part) => part === "" || !Number.isFinite(Number(part)))) throw new Error(`Stop ${index}: use latitude, longitude, optionally followed by four fleet values.`);
      const values = pieces.map(Number);
      const stop = { lat: values[0], lon: values[1] };
      if (values.length === 6) [stop.demand, stop.earliest, stop.latest, stop.service_time] = values.slice(2);
      return stop;
    });
  }

  function payloadFromForm(solver) {
    const fleet = byId("problem").value === "CVRPTW";
    return {
      stops: parseStops(), problem: byId("problem").value, provider: byId("provider").value,
      solver: solver || byId("solver").value, vehicles: fleet ? Number(byId("vehicles").value) : 1,
      capacity: Number(byId("capacity").value), shift_end: Number(byId("shift").value) * 60,
      wall_time_ms: Number(byId("budget").value),
    };
  }

  async function solve(payload) {
    return request("/api/solve", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  }

  function svgElement(tag, attrs, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([name, value]) => node.setAttribute(name, value));
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function pausePlayback() {
    if (playback) { cancelAnimationFrame(playback.frame); playback.frame = null; playback.last = null; }
    byId("play-route").textContent = "Play route";
  }

  function setMapView(view) {
    const map = byId("route-map"), width = map.getBoundingClientRect().width;
    if (!width) return; // Hidden tabs have no display scale; resize observation fits them on reveal.
    mapView = view; map.setAttribute("viewBox", view.join(" "));
    const unit = view[2] / width;
    map.querySelectorAll(".map-node").forEach((node) => node.setAttribute("r", (Number(node.dataset.node) ? 4 : 9) * unit));
    map.querySelectorAll(".map-node-label").forEach((label) => label.setAttribute("font-size", 13 * unit));
    if (playback) { playback.vehicle.dataset.scale = unit; paintPlayback(); }
  }

  function fitMap(stopsOnly = false) {
    const map = byId("route-map"), rect = map.getBoundingClientRect();
    const points = stopsOnly ? [...map.querySelectorAll(".map-node")].map((node) => [Number(node.getAttribute("cx")), Number(node.getAttribute("cy"))]) : [[0, 0], [900, 550]];
    setMapView(motion.fitView(points, rect.width / Math.max(1, rect.height), stopsOnly ? 32 : 0));
  }

  function zoomMap(factor, centre) {
    const rect = byId("route-map").getBoundingClientRect(), maxWidth = Math.max(900, 550 * rect.width / Math.max(1, rect.height));
    const width = Math.max(112.5, Math.min(maxWidth, mapView[2] * factor)), height = width * mapView[3] / mapView[2];
    const [x, y] = centre || [mapView[0] + mapView[2] / 2, mapView[1] + mapView[3] / 2];
    setMapView([x - width / 2, y - height / 2, width, height]);
  }

  function describeStop(node) {
    if (!currentResult) return;
    const owner = currentResult.routes.find((route) => route.sequence.includes(node)), i = owner?.sequence.indexOf(node);
    const point = currentResult.stops[node];
    byId("stop-detail").textContent = `${node ? `Stop ${node}` : "Depot"} · ${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}${owner ? ` · Vehicle ${owner.vehicle_id}, visit ${i + 1} of ${owner.sequence.length} · arrival ${clock(owner.schedule.arrival[i])} elapsed` : node ? " · Unserved" : " · Start and return point"}.`;
  }

  function paintPlayback(follow = false) {
    if (!playback?.track.length) return;
    const p = playback, position = motion.position(p.track, p.progress), done = position.completed;
    if (follow && (position.x < mapView[0] + 24 || position.x > mapView[0] + mapView[2] - 24 || position.y < mapView[1] + 24 || position.y > mapView[1] + mapView[3] - 24)) zoomMap(1, [position.x, position.y]);
    p.vehicle.style.transform = `translate(${position.x}px, ${position.y}px)`;
    p.vehicle.firstChild.style.transform = `rotate(${position.angle}deg) scale(${p.vehicle.dataset.scale || 1})`;
    if (p.painted !== done) {
      p.legs.forEach((line, i) => { line.style.opacity = i === position.leg ? "1" : i < done && i >= done - 3 ? ".3" : "0"; });
      const visited = new Set(p.route.sequence.slice(0, done));
      p.markers.forEach(({ node, marker, label }) => {
        marker.classList.toggle("visited", visited.has(node));
        marker.classList.toggle("selected-stop", node === selectedStop);
        const next = p.route.nodes[Math.min(p.route.nodes.length - 1, done + 1)];
        marker.classList.toggle("next-stop", node === next);
        label.style.opacity = !node || byId("map-labels").checked || node === selectedStop || node === next || node === p.route.nodes[done] ? "1" : "0";
      });
      const count = Math.min(done, p.route.sequence.length);
      byId("playback-count").textContent = `${count} / ${p.route.sequence.length} stops visited`;
      byId("playback-status").textContent = done >= p.track.length ? `Vehicle ${p.route.vehicle_id} returned to depot` : `Vehicle ${p.route.vehicle_id} · ${p.route.nodes[done] || "Depot"} → ${p.route.nodes[done + 1] || "Depot"}`;
      p.painted = done;
    }
    byId("route-progress").value = p.progress;
    byId("route-progress").setAttribute("aria-valuetext", `${Math.min(done, p.route.sequence.length)} of ${p.route.sequence.length} deliveries; ${done >= p.track.length ? "returned to depot" : "route in progress"}`);
  }

  function playFrame(now) {
    const p = playback;
    if (!p || document.hidden || byId("dispatch").hidden) { pausePlayback(); return; }
    if (p.last !== null) p.progress = Math.min(p.track.length, p.progress + Math.min(100, now - p.last) * Number(byId("playback-speed").value) / 700);
    p.last = now; paintPlayback(true);
    if (p.progress >= p.track.length) pausePlayback();
    else p.frame = requestAnimationFrame(playFrame);
  }

  function drawMap(preserve = false) {
    if (!currentResult) return;
    const old = preserve ? playback : null; pausePlayback();
    const data = currentResult, filter = byId("route-filter").value;
    const visible = data.routes.filter((route) => filter === "all" || String(route.vehicle_id) === filter);
    const lines = visible.map((route) => route.geometry ? { route, points: motion.decodePolyline(route.geometry.polyline), road: true } : data.provenance.geometry_kind === "straight_line_estimate" ? { route, points: route.nodes.map((i) => data.stops[i]), road: false } : { route, points: [], road: true });
    const points = [...data.stops, ...lines.flatMap((line) => line.points)];
    // ponytail: city-scale projection; add a tile map only when global navigation is required.
    const centreLat = points.reduce((sum, point) => sum + point.lat, 0) / points.length;
    const lonScale = Math.max(0.01, Math.cos(centreLat * Math.PI / 180));
    // Avoid spreading long road geometries into function arguments.
    const bounds = points.reduce((b, p) => [Math.min(b[0], p.lon * lonScale), Math.max(b[1], p.lon * lonScale), Math.min(b[2], -p.lat), Math.max(b[3], -p.lat)], [Infinity, -Infinity, Infinity, -Infinity]);
    const [minX, maxX, minY, maxY] = bounds;
    const scale = Math.min(780 / Math.max(maxX - minX, .00001), 430 / Math.max(maxY - minY, .00001));
    const project = (p) => [450 + (p.lon * lonScale - (minX + maxX) / 2) * scale, 275 + (-p.lat - (minY + maxY) / 2) * scale];
    const map = byId("route-map"); map.replaceChildren();
    map.classList.toggle("dense-map", data.stops.length > 30);
    map.closest(".dispatch-dashboard").classList.toggle("dense-dashboard", data.stops.length > 30);
    const route = visible[0], colour = routeColours[(route?.vehicle_id || 0) % routeColours.length];
    lines.forEach((line) => { if (line.points.length && byId("map-overview").checked) map.append(svgElement("polyline", { points: line.points.map((p) => project(p).join(",")).join(" "), class: "route-context", fill: "none", stroke: routeColours[line.route.vehicle_id % routeColours.length], "stroke-width": 2, opacity: .22, "stroke-linejoin": "round", "stroke-dasharray": line.road ? "none" : "8 5" })); });
    let paths = [];
    if (route && data.provenance.geometry_kind === "straight_line_estimate") paths = route.nodes.slice(1).map((node, i) => [project(data.stops[route.nodes[i]]), project(data.stops[node])]);
    else if (route?.geometry?.leg_polylines?.length === route.nodes.length - 1) paths = route.geometry.leg_polylines.map((steps) => steps.flatMap((line) => motion.decodePolyline(line)).map(project));
    if (paths.some((path) => !path.length)) paths = [];
    const legs = paths.map((path) => svgElement("polyline", { points: path.map((p) => p.join(",")).join(" "), class: "route-leg", fill: "none", stroke: colour, "stroke-width": 3.5, "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": data.provenance.geometry_kind === "road" ? "none" : "7 5", opacity: 0 }));
    legs.forEach((line) => map.append(line));
    mapPositions = new Map(data.stops.map((point, node) => [node, project(point)]));
    if (paths.length) { mapPositions.set(0, paths[0][0]); paths.forEach((path, i) => mapPositions.set(route.nodes[i + 1], path.at(-1))); }
    const visibleNodes = new Set(visible.flatMap((route) => route.nodes));
    const markers = [];
    data.stops.forEach((point, index) => {
      if (filter !== "all" && !visibleNodes.has(index)) return;
      const owner = data.routes.find((route) => route.nodes.includes(index));
      const [x, y] = mapPositions.get(index), marker = svgElement("circle", { cx: x, cy: y, r: index ? (data.stops.length > 30 ? 3.5 : 6) : 9, class: `map-node${data.unserved.includes(index) ? " unserved" : ""}`, "data-node": index, fill: index ? "#8e9da9" : "#193c50", stroke: "#fff", "stroke-width": 1.5 });
      marker.append(svgElement("title", {}, `${index ? `Stop ${index}` : "Depot"}: ${point.lat}, ${point.lon}`));
      const label = svgElement("text", { x: x + 10, y: y - 10, class: "map-node-label", "font-size": 13, "font-weight": 700, "pointer-events": "none" }, index || "D");
      label.style.opacity = !index || byId("map-labels").checked || index === selectedStop ? "1" : "0";
      map.append(marker, label); markers.push({ node: index, marker, label });
    });
    const vehicle = svgElement("g", { class: "map-vehicle", "aria-hidden": "true" });
    const body = svgElement("g", {}); body.append(svgElement("rect", { x: -16, y: -10, width: 21, height: 19, rx: 3, fill: colour, stroke: "#fff", "stroke-width": 2 }), svgElement("path", { d: "M5 -7H12L18 0V9H5Z", fill: colour, stroke: "#fff", "stroke-width": 2 }), svgElement("path", { d: "M9 -5H11L15 0H9Z", fill: "#d9edf7" }), svgElement("circle", { cx: -10, cy: 10, r: 4, fill: "#193c50" }), svgElement("circle", { cx: 11, cy: 10, r: 4, fill: "#193c50" })); vehicle.append(body);
    playback = paths.length ? { route, track: motion.buildTrack(paths), progress: old?.route.vehicle_id === route.vehicle_id ? old.progress : 0, legs, markers, vehicle, frame: null, last: null, painted: null } : null;
    byId("route-progress").max = paths.length || 1;
    if (playback) { map.append(vehicle); paintPlayback(); }
    else {
      byId("playback-status").textContent = route ? "Per-leg road geometry unavailable. Re-solve to enable playback." : "No served route to play.";
      byId("playback-count").textContent = `0 / ${route?.sequence.length || 0} stops replayed`;
      byId("route-progress").value = 0;
    }
    for (const id of ["play-route", "step-route", "reset-route", "route-progress"]) byId(id).disabled = !playback;
    byId("play-route").disabled = !playback || reducedMotion.matches;
    byId("play-route").title = reducedMotion.matches ? "Reduced motion is enabled. Use Next stop or the progress slider." : "Play the calculated route";
    const stops = byId("map-stop"); stops.replaceChildren();
    data.stops.forEach((_, node) => { if (filter === "all" || visibleNodes.has(node)) { const option = element("option", node ? `Stop ${node}${data.unserved.includes(node) ? " · unserved" : ""}` : "Depot"); option.value = node; stops.append(option); } });
    if (![...stops.options].some((option) => Number(option.value) === selectedStop)) selectedStop = 0;
    stops.value = selectedStop; stops.disabled = !data.stops.length; describeStop(selectedStop);
    if (!preserve) fitMap(data.stops.length > 30);
    else setMapView(mapView);
  }

  function clock(seconds) {
    const h = Math.floor(seconds / 3600), m = Math.floor(seconds % 3600 / 60), s = seconds % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function statusClass(status) {
    if (status === "PROVEN_OPTIMAL_TSP") return "proven";
    if (status === "HEURISTIC_FEASIBLE_TSP" || status === "HEURISTIC_FEASIBLE_CVRPTW") return "feasible";
    if (status.includes("TIMEOUT") || status.includes("PARTIAL")) return "partial";
    return "infeasible";
  }

  function metric(label, value, copy) {
    const card = element("section", undefined, "card metric"); card.append(element("p", label, "label"), element("p", value, "metric-value"), element("p", copy, "metric-copy")); return card;
  }

  function table(headers, rows) {
    const wrap = element("div", undefined, "table-wrap"), node = element("table"), head = element("thead"), hr = element("tr");
    headers.forEach((value) => hr.append(element("th", value))); head.append(hr); const body = element("tbody");
    rows.forEach((values) => { const row = element("tr"); values.forEach((value) => row.append(element("td", value))); body.append(row); }); node.append(head, body); wrap.append(node); return wrap;
  }

  function renderFleet(data, payload) {
    const target = byId("fleet-utilization"); target.className = "fleet-list"; target.replaceChildren();
    byId("fleet-count").textContent = `${data.routes.length} used / ${payload.vehicles} available`;
    byId("route-details-title").textContent = payload.problem === "TSP" ? "Tour coverage" : "Vehicle fleet utilization";
    for (const route of data.routes) {
      const capacity = payload.problem === "CVRPTW" ? payload.capacity : data.stops.length - 1;
      const used = payload.problem === "CVRPTW" ? route.load : route.sequence.length;
      const percent = Math.min(100, Math.round(used / capacity * 100));
      const card = element("article", undefined, "fleet-item");
      const heading = element("div", undefined, "fleet-heading");
      const swatch = element("span", undefined, "vehicle-swatch"); swatch.style.background = routeColours[route.vehicle_id % routeColours.length];
      heading.append(swatch, element("strong", `Vehicle ${route.vehicle_id}`), element("span", `${route.sequence.length} stops`, "metric-copy"));
      const label = element("div", undefined, "util-label"); label.append(element("span", payload.problem === "CVRPTW" ? "Parcel load" : "Customers visited"), element("strong", `${used} / ${capacity} (${percent}%)`));
      const meter = element("div", undefined, "util-meter"); const fill = element("span"); fill.style.width = `${percent}%`; fill.style.background = routeColours[route.vehicle_id % routeColours.length]; meter.append(fill);
      card.append(heading, label, meter, element("p", `${route.cost.toLocaleString()} metres · return ${clock(route.schedule.return_to_depot)} elapsed`, "metric-copy")); target.append(card);
    }
    if (data.unserved.length) target.append(element("p", `${data.unserved.length} stops unserved`, "error"));
  }

  function renderTimeline() {
    if (!currentResult) return;
    const filter = byId("route-filter").value;
    const route = currentResult.routes.find((item) => String(item.vehicle_id) === filter) || currentResult.routes[0];
    const target = byId("eta-timeline"); target.className = "timeline"; target.replaceChildren();
    if (!route) { target.className = "timeline empty"; target.textContent = "No route was produced."; return; }
    byId("timeline-label").textContent = `Vehicle ${route.vehicle_id} · elapsed time`;
    const depot = element("article", undefined, "timeline-stop"); depot.append(element("strong", "D · Depot"), element("time", "00:00:00")); target.append(depot);
    route.sequence.forEach((node, index) => {
      const stop = element("article", undefined, "timeline-stop");
      stop.append(element("strong", `${node} · Stop ${node}`), element("time", clock(route.schedule.arrival[index])), element("small", `${currentResult.stops[node].lat.toFixed(5)}, ${currentResult.stops[node].lon.toFixed(5)} · depart ${clock(route.schedule.departure[index])}`)); target.append(stop);
    });
    const returned = element("article", undefined, "timeline-stop"); returned.append(element("strong", "D · Return to depot"), element("time", clock(route.schedule.return_to_depot))); target.append(returned);
  }

  function updateShell(data, payload) {
    byId("header-matrix").textContent = data.matrix_metadata.sha256.slice(0, 10);
    byId("header-symmetry").textContent = data.matrix_metadata.symmetric ? "d(A,B) = d(B,A)" : "d(A,B) ≠ d(B,A)";
    byId("header-symmetry").className = data.matrix_metadata.symmetric ? "symmetric-copy" : "asymmetric-copy";
    byId("instance-type").textContent = payload.problem;
    byId("instance-stops").textContent = data.stops.length;
    byId("instance-vehicles").textContent = payload.vehicles;
    byId("instance-matrix").textContent = `${data.matrix_metadata.symmetric ? "Symmetric" : "Asymmetric"} ${data.provenance.provider === "osrm" ? "road" : "estimate"}`;
    byId("hero-title").textContent = datasetName;
    byId("hero-meta").textContent = `${data.stops.length} stops · ${payload.vehicles} ${payload.vehicles === 1 ? "vehicle" : "vehicles"} · hash ${data.matrix_metadata.sha256.slice(0, 10)}`;
    byId("hero-description").textContent = `${data.headline}. Independent feasibility: ${data.feasible ? "passed" : "failed"}; provider: ${data.provenance.provider}.`;
    renderFleet(data, payload); renderTimeline();
  }

  function showResult(data, payload) {
    pausePlayback(); selectedStop = 0;
    currentResult = data; currentPayload = payload;
    const badge = byId("result-status"); badge.textContent = data.report.status.replaceAll("_", " "); badge.className = `status ${statusClass(data.report.status)}`;
    byId("result-summary").replaceChildren(element("p", data.headline, "result-headline"), element("p", `${solverLabel(data.report.solver_name)} · ${data.routes.length} used vehicles · ${data.unserved.length} unserved · solver ${data.report.wall_time_ms.toFixed(3)} ms`, "metric-copy"));
    [...data.violations, ...data.warnings].forEach((message) => byId("result-summary").append(element("p", message, "error")));
    byId("map-caption").textContent = data.provenance.geometry_kind === "road" ? "OSRM road geometry · Road-snapped playback stops · D = depot" : "Offline estimate · Dashed lines are not road geometry · D = depot";
    byId("map-overview").checked = data.stops.length <= 30;
    byId("map-labels").checked = data.stops.length <= 30;
    const selector = byId("route-filter"); selector.replaceChildren(element("option", "All vehicles")); selector.firstChild.value = "all";
    data.routes.forEach((route) => { const option = element("option", `Vehicle ${route.vehicle_id}`); option.value = route.vehicle_id; selector.append(option); }); selector.disabled = !data.routes.length;
    const schedules = byId("schedules"); schedules.replaceChildren();
    data.routes.forEach((route) => {
      const section = element("section"); section.append(element("h3", `Vehicle ${route.vehicle_id} · ${payload.problem === "TSP" ? `${route.sequence.length} customers` : `${route.load} parcels`} · ${route.cost.toLocaleString()} metres · return ${clock(route.schedule.return_to_depot)}`));
      const rows = route.sequence.map((node, i) => [node, clock(route.schedule.arrival[i]), route.schedule.wait[i], clock(route.schedule.arrival[i] + route.schedule.wait[i]), clock(route.schedule.departure[i])]);
      section.append(table(["Stop", "Arrival", "Wait (s)", "Service start", "Departure"], rows)); schedules.append(section);
    });
    byId("result-json").textContent = JSON.stringify(data, null, 2); byId("schedule-section").hidden = false; updateShell(data, payload); drawMap(); renderReport();
  }

  function download(name, value, type) {
    const link = document.createElement("a"), url = URL.createObjectURL(new Blob([value], { type })); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url);
  }

  function reportMarkdown() {
    if (!currentResult) throw new Error("Calculate a route first.");
    const d = currentResult, lines = ["# Courier Delivery Route Optimization System", "", "DAA concepts: TSP, Greedy, Branch & Bound. CVRPTW is an optional extension.", "", `**Model:** ${d.report.problem_type}`, `**Algorithm:** ${solverLabel(d.report.solver_name)}`, `**Claim:** ${d.headline}`, `**Status:** ${d.report.status}`, `**Feasible:** ${d.feasible ? "yes" : "no"}`, `**Objective:** ${d.report.objective_value} ${d.report.objective_units}`, `**Matrix SHA-256:** ${d.matrix_metadata.sha256}`, `**Input SHA-256:** ${d.provenance.input_sha256}`, "", "## Routes", ""];
    d.routes.forEach((r) => lines.push(`- Vehicle ${r.vehicle_id}: depot → ${r.sequence.join(" → ")} → depot; load ${r.load}; cost ${r.cost}`));
    if (comparisonForResult()) {
      lines.push("", "## Same-input algorithm comparison", "", "| Algorithm | Status | Distance | Explored | Pruned | Lower bound | Solver ms | Stop reason |", "| --- | --- | --- | --- | --- | --- | --- | --- |");
      comparison.results.forEach(({ report: r }) => lines.push(`| ${solverLabel(r.solver_name)} | ${r.status} | ${r.objective_value} | ${r.nodes_explored} | ${r.nodes_pruned} | ${r.best_lower_bound ?? "—"} | ${r.wall_time_ms.toFixed(3)} | ${r.stop_reason} |`));
      lines.push("", "Runtimes are measurements of this run, not a general performance ranking. Optimality applies only when the returned status is PROVEN_OPTIMAL_TSP.");
    }
    lines.push("", "## Reproducibility", "", `- Solver: ${d.report.solver_name}`, `- Stop reason: ${d.report.stop_reason}`, `- Provider: ${d.provenance.provider_fingerprint}`, `- Git revision: ${d.provenance.git_revision}${d.provenance.git_dirty ? " (dirty)" : ""}`); return lines.join("\n");
  }

  function comparisonForResult() {
    if (!comparison || !currentResult) return false;
    const { solver: ignored, ...input } = currentPayload;
    const { solver: ignoredBase, ...base } = comparison.payload;
    return JSON.stringify(input) === JSON.stringify(base) && comparison.results[0].matrix_metadata.sha256 === currentResult.matrix_metadata.sha256;
  }

  function comparisonTable(results) {
    const costs = results.filter((r) => r.feasible).map((r) => r.report.objective_value);
    const best = costs.length ? Math.min(...costs) : null;
    return table(["Algorithm", "Status", "Distance", "Gap to best feasible", "Explored", "Pruned", "Lower bound", "Solver ms", "Stop reason"], results.map(({ report: r, feasible }) => [
      solverLabel(r.solver_name), r.status, `${r.objective_value} ${r.objective_units}`,
      !feasible || best === null ? "—" : best === 0 ? (r.objective_value === 0 ? "0.00%" : "undefined (zero baseline)") : `${((r.objective_value - best) / best * 100).toFixed(2)}%`,
      r.nodes_explored, r.nodes_pruned, r.best_lower_bound ?? "—", r.wall_time_ms.toFixed(3), r.stop_reason,
    ]));
  }

  function renderReport() {
    if (!currentResult) return;
    const d = currentResult, body = byId("report-body"); body.replaceChildren(element("p", "Waybill · dispatch report", "eyebrow"), element("h2", d.headline));
    body.append(element("p", `Model: ${d.report.problem_type} · Algorithm: ${solverLabel(d.report.solver_name)}`, "metric-copy"));
    body.append(metric("Status", d.report.status.replaceAll("_", " "), `Stopped: ${d.report.stop_reason}`), metric("Objective", `${d.report.objective_value.toLocaleString()} ${d.report.objective_units}`, `${d.routes.length} used vehicles`), metric("Feasibility", d.feasible ? "passed" : "failed", d.feasible ? "Independent checker found no violation." : d.violations.join("; ")));
    body.append(element("h3", "Routes"), table(["Vehicle", "Sequence", "Load", "Cost", "Depot return"], d.routes.map((r) => [r.vehicle_id, `D → ${r.sequence.join(" → ")} → D`, r.load, r.cost, clock(r.schedule.return_to_depot)])), element("h3", "Provenance"));
    const pre = element("pre", JSON.stringify({ input_sha256: d.provenance.input_sha256, matrix_sha256: d.matrix_metadata.sha256, provider: d.provenance.provider_fingerprint, git_revision: d.provenance.git_revision, git_dirty: d.provenance.git_dirty, budget: d.provenance.budget }, null, 2)); body.append(pre);
    if (comparisonForResult()) body.append(element("h3", "Same-input algorithm comparison"), comparisonTable(comparison.results));
  }

  async function runComparison() {
    const button = byId("compare-solvers"), error = byId("compare-error"); error.textContent = ""; setBusy(button, true, "Running…", "Run comparison");
    try {
      comparison = null;
      byId("comparison-summary").replaceChildren(); byId("comparison-routes").replaceChildren(); byId("comparison-conclusion").textContent = "";
      byId("comparison-table").replaceChildren(element("p", "Computing algorithms on the selected input…")); renderReport();
      const base = payloadFromForm(), methods = base.problem === "CVRPTW" ? ["savings"] : ["nearest_neighbor", "branch_and_bound"];
      if (base.problem === "TSP" && byId("include-held-karp").checked) {
        if (base.stops.length > 17) throw new Error("Held–Karp cross-check is limited to 17 nodes. Uncheck it to compare Greedy with Branch & Bound.");
        methods.push("held_karp");
      }
      const results = [];
      for (const solver of methods) results.push(await solve({ ...base, solver }));
      if (new Set(results.map((r) => r.matrix_metadata.sha256)).size !== 1) throw new Error("Matrix identity changed between solver runs.");
      if (JSON.stringify(payloadFromForm()) !== JSON.stringify(base)) throw new Error("Inputs changed during comparison. Run it again for the updated input.");
      comparison = { payload: base, results };
      const costs = results.filter((r) => r.feasible).map((r) => r.report.objective_value), best = costs.length ? Math.min(...costs) : null;
      const proven = results.find((r) => r.report.status === "PROVEN_OPTIMAL_TSP");
      byId("comparison-summary").replaceChildren(metric("Algorithms", results.length, "Same input and matrix"), metric("Best feasible distance", best === null ? "None" : best.toLocaleString(), results[0].report.objective_units), metric("Proof", proven ? "Optimal" : "Unproven", proven ? `${solverLabel(proven.report.solver_name)} completed a proof` : "Best found is not an optimality certificate"));
      byId("comparison-table").className = ""; byId("comparison-table").replaceChildren(comparisonTable(results));
      const greedy = results[0], exact = results[1];
      byId("comparison-conclusion").textContent = exact && greedy.feasible && exact.feasible ? `Branch & Bound ${exact.report.status === "PROVEN_OPTIMAL_TSP" ? "proved an optimal tour" : "returned a feasible tour; optimality is unproven"}. Distance change from Greedy: ${(greedy.report.objective_value - exact.report.objective_value).toLocaleString()} ${exact.report.objective_units}. Runtimes are for these runs only. Matrix SHA-256: ${greedy.matrix_metadata.sha256}.` : "No Greedy / Branch & Bound conclusion is available for this model and feasibility state.";
      results.forEach((result, index) => {
        const view = element("button", `View ${solverLabel(result.report.solver_name)} tour`, "secondary"); view.type = "button";
        view.addEventListener("click", () => { showResult(result, { ...base, solver: methods[index] }); activateTab("dispatch"); }); byId("comparison-routes").append(view);
      });
      const displayed = (proven && proven.report.objective_value === best ? proven : results.find((r) => r.feasible && r.report.objective_value === best)) || results[0];
      showResult(displayed, { ...base, solver: methods[results.indexOf(displayed)] });
    } catch (e) { error.textContent = e.message; byId("comparison-table").textContent = "Comparison did not complete. Resolve the error and run again."; } finally { setBusy(button, false, "Running…", "Run comparison"); }
  }

  async function auditAsymmetry() {
    const button = byId("audit-asymmetry"), error = byId("asymmetry-error"); error.textContent = ""; setBusy(button, true, "Auditing…", "Audit matrix");
    try {
      const result = await solve(payloadFromForm()), differences = [];
      for (let i = 0; i < result.matrix.length; i++) for (let j = i + 1; j < result.matrix.length; j++) { const forward = result.matrix[i][j], reverse = result.matrix[j][i], delta = Math.abs(forward - reverse); differences.push({ i, j, forward, reverse, delta }); }
      const changed = differences.filter((x) => x.delta), max = Math.max(0, ...differences.map((x) => x.delta)), mean = differences.length ? differences.reduce((s, x) => s + x.delta, 0) / differences.length : 0;
      byId("asymmetry-metrics").replaceChildren(metric("Directed pairs", differences.length, `${changed.length} differ`), metric("Largest difference", `${max.toLocaleString()} ${result.matrix_metadata.unit}`, "Absolute A↔B delta"), metric("Mean difference", mean.toFixed(1), result.provenance.provider));
      byId("asymmetry-table").className = ""; byId("asymmetry-table").replaceChildren(table(["Pair", "A → B", "B → A", "Difference"], differences.sort((a, b) => b.delta - a.delta).slice(0, 12).map((x) => [`${x.i} ↔ ${x.j}`, x.forward, x.reverse, x.delta])));
    } catch (e) { error.textContent = e.message; } finally { setBusy(button, false, "Auditing…", "Audit matrix"); }
  }

  function renderEvidence() {
    const evidence = window.WAYBILL_EVIDENCE, summary = byId("evidence-summary"), ledger = byId("evidence-ledger");
    if (!evidence || !Array.isArray(evidence.records)) { ledger.replaceChildren(element("p", "No evidence bundle found. Run `make evidence`.", "empty")); return; }
    const exact = evidence.records.filter((x) => x.result.status === "PROVEN_OPTIMAL_TSP"), fleet = evidence.records.find((x) => x.result.problem_type === "CVRPTW");
    summary.replaceChildren(metric("Recorded runs", evidence.records.length, "Generated bundle"), metric("Exact proofs", exact.length, "Typed proof status"), metric("Fleet gate", fleet ? fleet.result.status.replaceAll("HEURISTIC_", "") : "missing", "Independent feasibility"));
    ledger.replaceChildren(table(["Input", "Solver", "Status", "Objective", "Lower bound", "Wall ms"], evidence.records.map(({ manifest, result }) => [manifest.input_name, manifest.solver_name, result.status, `${result.objective_value} ${result.objective_unit}`, result.best_lower_bound ?? "—", Number(result.wall_time_ms).toFixed(2)])));
    const details = element("details", undefined, "card evidence-details"), heading = element("summary", "Bundle provenance"); details.append(heading, element("pre", JSON.stringify({ content_sha256: evidence.content_sha256, schema_version: evidence.schema_version, metadata: evidence.metadata }, null, 2))); ledger.append(details);
  }

  function auditResult(data) {
    const served = data.routes.flatMap((r) => r.sequence), expected = data.stops.map((_, i) => i).slice(1), routeCost = data.routes.reduce((sum, r) => sum + r.cost, 0);
    const checks = [
      ["Matrix identity", data.matrix_metadata.sha256 === data.report.distance_matrix_hash, "Response matrix matches SolveReport."],
      ["Objective reconstruction", routeCost === data.report.objective_value, `${routeCost} from route costs.`],
      ["Visit partition", [...served, ...data.unserved].sort((a, b) => a - b).join() === expected.join(), "Every customer is served or explicitly unserved."],
      ["No duplicate visits", new Set(served).size === served.length, `${served.length} visits checked.`],
      ["Feasibility agreement", data.feasible === (data.violations.length === 0), "Boolean agrees with independent violations."],
      ["Route scoring", data.routes.every((r) => r.cost === r.nodes.slice(1).reduce((sum, node, i) => sum + data.matrix[r.nodes[i]][node], 0)), "All arcs re-scored from returned matrix."],
      ["Input provenance", /^[a-f0-9]{64}$/.test(data.provenance.input_sha256), data.provenance.input_sha256],
    ];
    const list = byId("invariant-results"); list.className = "check-list"; list.replaceChildren(); checks.forEach(([name, pass, copy]) => { const row = element("section", undefined, `check ${pass ? "check-pass" : "check-fail"}`); row.append(element("strong", `${pass ? "PASS" : "FAIL"} · ${name}`), element("p", copy, "metric-copy")); list.append(row); });
  }

  async function runInvariants() {
    const button = byId("run-invariants"), error = byId("invariant-error"); error.textContent = ""; setBusy(button, true, "Checking…", "Run invariants");
    try { const payload = payloadFromForm(), result = await solve(payload); showResult(result, payload); auditResult(result); } catch (e) { error.textContent = e.message; } finally { setBusy(button, false, "Checking…", "Run invariants"); }
  }

  function activateTab(name, focus) {
    if (name !== "dispatch") pausePlayback();
    document.querySelectorAll(".app-panel").forEach((panel) => { panel.hidden = panel.id !== name; });
    document.querySelectorAll(".nav-tab[data-tab]").forEach((button) => { const active = button.dataset.tab === name; button.setAttribute("aria-selected", active); if (active) { button.scrollIntoView({ block: "nearest", inline: "nearest" }); if (focus) button.focus(); } });
    history.replaceState(null, "", `#${name}`);
  }

  function inputEdited() {
    pausePlayback();
    comparison = null;
    byId("comparison-summary").replaceChildren(); byId("comparison-routes").replaceChildren(); byId("comparison-conclusion").textContent = "";
    byId("comparison-table").className = "empty"; byId("comparison-table").textContent = "Inputs changed. Run comparison for the updated input.";
    if (currentResult) byId("hero-description").textContent = `Inputs edited. The displayed tour is the last calculated result (${solverLabel(currentResult.report.solver_name)}). Solve again to update it.`;
    renderReport();
  }

  async function importFile(file) {
    if (!file) return; if (file.size > 65536) throw new Error("Import must be 64 KB or smaller.");
    const text = await file.text(); let stops;
    if (file.name.toLowerCase().endsWith(".json")) { const value = JSON.parse(text); stops = Array.isArray(value) ? value : value.stops; if (!Array.isArray(stops)) throw new Error("JSON must be a stop array or contain a stops array."); }
    else {
      const lines = text.trim().split(/\n+/), rows = lines.map((line) => line.split(",").map((v) => v.trim()));
      if (rows[0] && !Number.isFinite(Number(rows[0][0]))) rows.shift();
      stops = rows.map((r) => { if (![2, 6].includes(r.length) || r.some((v) => !Number.isFinite(Number(v)))) throw new Error("CSV rows need 2 or 6 numeric columns."); const v = r.map(Number), s = { lat: v[0], lon: v[1] }; if (v.length === 6) [s.demand, s.earliest, s.latest, s.service_time] = v.slice(2); return s; });
    }
    if (stops.length < 2 || stops.length > 100) throw new Error("Import needs 2–100 stops.");
    byId("stops").value = stops.map((s) => [s.lat, s.lon, ...(s.demand === undefined ? [] : [s.demand, s.earliest, s.latest, s.service_time])].join(", ")).join("\n");
    datasetName = file.name; const custom = byId("dataset-selector").querySelector('[value="custom"]'); custom.disabled = false; custom.textContent = file.name; byId("dataset-selector").value = "custom"; byId("import-error").textContent = "";
    importedInput = byId("stops").value; importedName = file.name; inputEdited(); activateTab("dispatch");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault(); const button = byId("solve-button"), normal = byId("problem").value === "CVRPTW" ? "Dispatch fleet" : "Solve tour"; byId("solve-error").textContent = ""; setBusy(button, true, "Calculating…", normal);
    try { const payload = payloadFromForm(), result = await solve(payload); showResult(result, payload); } catch (e) { byId("solve-error").textContent = e.message; } finally { setBusy(button, false, "Calculating…", normal); }
  });
  byId("problem").addEventListener("change", chooseModel); byId("route-filter").addEventListener("change", () => { selectedStop = 0; drawMap(); renderTimeline(); });
  byId("play-route").addEventListener("click", () => {
    if (!playback || reducedMotion.matches) return;
    if (playback.frame !== null) { pausePlayback(); return; }
    if (playback.progress >= playback.track.length) playback.progress = 0;
    playback.last = null; byId("play-route").textContent = "Pause route";
    playback.frame = requestAnimationFrame(playFrame);
  });
  byId("step-route").addEventListener("click", () => { pausePlayback(); if (playback) { playback.progress = Math.min(playback.track.length, Math.floor(playback.progress) + 1); paintPlayback(true); } });
  byId("reset-route").addEventListener("click", () => { pausePlayback(); if (playback) { playback.progress = 0; paintPlayback(true); } });
  byId("route-progress").addEventListener("input", () => { pausePlayback(); if (playback) { playback.progress = Number(byId("route-progress").value); paintPlayback(true); } });
  for (const id of ["map-overview", "map-labels"]) byId(id).addEventListener("change", () => drawMap(true));
  byId("map-zoom-in").addEventListener("click", () => zoomMap(.75));
  byId("map-zoom-out").addEventListener("click", () => zoomMap(1 / .75));
  byId("map-fit").addEventListener("click", () => fitMap());
  function inspectStop() {
    selectedStop = Number(byId("map-stop").value); pausePlayback();
    const owner = currentResult?.routes.find((route) => route.sequence.includes(selectedStop));
    if (owner && playback?.route.vehicle_id !== owner.vehicle_id) { byId("route-filter").value = owner.vehicle_id; drawMap(); renderTimeline(); }
    if (playback) { playback.painted = null; paintPlayback(); }
    describeStop(selectedStop);
    if (mapPositions.has(selectedStop)) zoomMap(Math.min(1, 375 / mapView[2]), mapPositions.get(selectedStop));
  }
  byId("map-stop").addEventListener("change", inspectStop);
  const map = byId("route-map"); let drag = null, moved = false;
  map.addEventListener("pointerdown", (event) => { if (event.button !== 0) return; drag = { x: event.clientX, y: event.clientY, view: [...mapView], node: event.target.closest("[data-node]")?.dataset.node }; moved = false; map.setPointerCapture(event.pointerId); });
  map.addEventListener("pointermove", (event) => {
    if (!drag) return; const bounds = map.getBoundingClientRect(), dx = event.clientX - drag.x, dy = event.clientY - drag.y;
    moved ||= Math.hypot(dx, dy) > 4;
    if (moved) setMapView([drag.view[0] - dx * drag.view[2] / bounds.width, drag.view[1] - dy * drag.view[3] / bounds.height, drag.view[2], drag.view[3]]);
  });
  map.addEventListener("pointerup", () => { const node = drag?.node; drag = null; if (!moved && node !== undefined) { byId("map-stop").value = node; inspectStop(); } });
  map.addEventListener("pointercancel", () => { drag = null; });
  map.addEventListener("keydown", (event) => {
    if (["+", "=", "-", "Escape", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) event.preventDefault();
    if (event.key === "+" || event.key === "=") zoomMap(.75);
    else if (event.key === "-") zoomMap(1 / .75);
    else if (event.key === "Escape") fitMap();
    else if (event.key.startsWith("Arrow")) { const shift = mapView[2] / 10; setMapView([mapView[0] + (event.key === "ArrowRight" ? shift : event.key === "ArrowLeft" ? -shift : 0), mapView[1] + (event.key === "ArrowDown" ? shift : event.key === "ArrowUp" ? -shift : 0), mapView[2], mapView[3]]); }
  });
  new IntersectionObserver(([entry]) => { if (!entry.isIntersecting) pausePlayback(); }).observe(map);
  new ResizeObserver(([entry]) => { if (entry.contentRect.width && currentResult) fitMap(currentResult.stops.length > 30); }).observe(map);
  document.addEventListener("visibilitychange", () => { if (document.hidden) pausePlayback(); });
  reducedMotion.addEventListener("change", () => { pausePlayback(); byId("play-route").disabled = !playback || reducedMotion.matches; });
  form.addEventListener("input", inputEdited);
  byId("dataset-selector").addEventListener("change", () => {
    const custom = byId("dataset-selector").value === "custom";
    byId("stops").value = custom ? importedInput : sampleInput;
    datasetName = custom ? importedName : byId("dataset-selector").firstElementChild.textContent.split(" · ")[0]; inputEdited();
  });
  byId("compare-topic").addEventListener("click", () => { activateTab("sandbox"); runComparison(); });
  byId("compare-solvers").addEventListener("click", runComparison); byId("audit-asymmetry").addEventListener("click", auditAsymmetry); byId("run-invariants").addEventListener("click", runInvariants);
  byId("import-file").addEventListener("change", (event) => importFile(event.target.files[0]).catch((e) => { byId("import-error").textContent = e.message; }));
  byId("download-input").addEventListener("click", () => { try { download("waybill-input.json", JSON.stringify({ stops: parseStops() }, null, 2), "application/json"); } catch (e) { byId("import-error").textContent = e.message; } });
  byId("download-result").addEventListener("click", () => { if (currentResult) download("waybill-result.json", JSON.stringify(currentResult, null, 2), "application/json"); });
  byId("download-report").addEventListener("click", () => { try { download("waybill-report.md", reportMarkdown(), "text/markdown"); } catch (e) { byId("report-body").replaceChildren(element("p", e.message, "error")); } });
  byId("print-report").addEventListener("click", () => window.print());
  byId("open-import").addEventListener("click", () => byId("import-file").click());
  byId("inspect-report").addEventListener("click", () => byId("solve-report-dialog").showModal());
  byId("close-report").addEventListener("click", () => byId("solve-report-dialog").close());
  document.querySelector(".brand").addEventListener("click", (event) => { event.preventDefault(); activateTab("dispatch"); });
  document.querySelectorAll(".nav-tab[data-tab]").forEach((button) => button.addEventListener("click", () => activateTab(button.dataset.tab)));
  document.querySelector(".app-nav").addEventListener("keydown", (event) => { if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return; const tabs = [...document.querySelectorAll(".nav-tab[data-tab]")], index = tabs.findIndex((x) => x.getAttribute("aria-selected") === "true"), next = (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length; event.preventDefault(); activateTab(tabs[next].dataset.tab, true); });

  chooseModel(); renderEvidence(); activateTab(location.hash.slice(1) && byId(location.hash.slice(1)) ? location.hash.slice(1) : "dispatch");
  if (location.protocol === "file:") { byId("engine-state").textContent = "Start `make live` and open the HTTP URL."; byId("solve-button").disabled = true; return; }
  Promise.all([request("/api/example"), request("/api/health")]).then(async ([example, health]) => {
    datasetName = example.name || "Monaco harbour deliveries"; byId("stops").value = example.stops.map((stop) => `${stop.lat}, ${stop.lon}`).join("\n"); byId("dataset-selector").firstElementChild.textContent = `${datasetName} · canonical live example`;
    sampleInput = byId("stops").value;
    byId("engine-state").textContent = health.osrm_available ? "Engine ready · OSRM connected" : "Engine ready · offline distances";
    if (!health.osrm_available) byId("provider").value = "haversine";
    const payload = payloadFromForm(); showResult(await solve(payload), payload);
  }).catch((e) => { byId("engine-state").textContent = "Engine unavailable"; byId("solve-error").textContent = e.message; });
}());
