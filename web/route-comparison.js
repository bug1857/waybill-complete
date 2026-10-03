/* Presentation only: route order, edge costs and feasibility come from the API. */
(function () {
  "use strict";
  const labels = { nearest_neighbor: "Greedy · nearest neighbour", branch_and_bound_min_in_out: "Branch & Bound", held_karp: "Held–Karp", clarke_wright_savings: "Clarke–Wright" };
  const label = (name) => labels[name] || name;
  const nodeLabel = (node) => node === 0 ? "D" : String(node);

  function edges(result) {
    return result.routes.flatMap((route, routeIndex) => route.nodes.slice(1).map((to, leg) => ({
      routeIndex, leg, from: route.nodes[leg], to, cost: result.matrix[route.nodes[leg]][to],
    })));
  }

  function selectEdge(result, step, departure = null) {
    const all = edges(result);
    return departure === null ? all[step] || null : all.find((edge) => edge.from === departure) || null;
  }

  function overlap(a, b) {
    // Directed edges, not geometrical road overlap: 1→3 differs from 3→1.
    const first = new Set(edges(a).map(({ from, to }) => `${from}:${to}`));
    const second = new Set(edges(b).map(({ from, to }) => `${from}:${to}`));
    return { shared: [...first].filter((edge) => second.has(edge)).length, total: first.size };
  }

  function sharedProjection(points) {
    if (!points.length) throw new Error("Comparison needs stop coordinates");
    const lonScale = Math.max(.01, Math.cos(points.reduce((s, p) => s + p.lat, 0) / points.length * Math.PI / 180));
    const bounds = points.reduce((b, p) => [Math.min(b[0], p.lon * lonScale), Math.max(b[1], p.lon * lonScale), Math.min(b[2], -p.lat), Math.max(b[3], -p.lat)], [Infinity, -Infinity, Infinity, -Infinity]);
    const [minX, maxX, minY, maxY] = bounds;
    const scale = Math.min(500 / Math.max(maxX - minX, .00001), 300 / Math.max(maxY - minY, .00001));
    return (p) => [300 + (p.lon * lonScale - (minX + maxX) / 2) * scale, 200 + (-p.lat - (minY + maxY) / 2) * scale];
  }

  function routeGeometry(result, decode) {
    return result.routes.map((route) => {
      if (result.provenance.geometry_kind === "straight_line_estimate") return {
        overview: route.nodes.map((n) => result.stops[n]),
        legs: route.nodes.slice(1).map((node, leg) => [result.stops[route.nodes[leg]], result.stops[node]]),
      };
      return {
        overview: route.geometry?.polyline ? decode(route.geometry.polyline) : [],
        legs: route.geometry?.leg_polylines?.map((leg) => leg.flatMap(decode)) || [],
      };
    });
  }

  function mount(container, { results, skipped, stopName, onOpen, decode }) {
    const el = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
    const svgEl = (tag, attrs, text) => { const node = document.createElementNS("http://www.w3.org/2000/svg", tag); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value)); if (text !== undefined) node.textContent = text; return node; };
    container.replaceChildren();
    const section = el("section", undefined, "comparison-map-section"), heading = el("div", undefined, "card-heading");
    heading.append(el("h2", "Same stops. Different journeys.")); section.append(heading);
    section.append(el("p", "Compare the next leg at the same visit step, or choose one departure stop to see where each algorithm goes next. D is the depot; numbers are stop IDs, not visit order.", "metric-copy"));
    const controls = el("div", undefined, "comparison-controls card"), stepGroup = el("div", undefined, "comparison-step-group");
    const stepLabel = el("label", "Visit step"); stepLabel.htmlFor = "comparison-step";
    const range = el("input"); range.type = "range"; range.id = "comparison-step"; range.min = 0; range.max = Math.max(0, ...results.map((r) => edges(r).length - 1)); range.step = 1; range.value = 0;
    const output = el("output"); output.htmlFor = range.id;
    const prev = el("button", "←", "secondary small-button"), next = el("button", "→", "secondary small-button");
    prev.type = next.type = "button"; prev.setAttribute("aria-label", "Previous comparison step"); next.setAttribute("aria-label", "Next comparison step");
    stepGroup.append(stepLabel, prev, range, next, output);
    const departGroup = el("div"), departLabel = el("label", "Or compare departing from"), depart = el("select"); departLabel.htmlFor = "comparison-departure"; depart.id = "comparison-departure";
    const stepOption = el("option", "Match by visit step"); stepOption.value = "step"; depart.append(stepOption);
    results[0].stops.forEach((_, n) => { const option = el("option", `${nodeLabel(n)} · ${stopName(n)}`); option.value = n; depart.append(option); });
    departGroup.append(departLabel, depart);
    const checks = el("div", undefined, "comparison-map-options"), full = el("input"), names = el("input"); full.type = names.type = "checkbox"; full.checked = results[0].stops.length <= 30; names.checked = results[0].stops.length <= 20;
    for (const [control, text] of [[full, "Full tour"], [names, "All stop IDs"]]) { const wrapper = el("label", undefined, "inline-check"); wrapper.append(control, document.createTextNode(` ${text}`)); checks.append(wrapper); }
    controls.append(stepGroup, departGroup, checks); section.append(controls);
    const status = el("p", undefined, "coverage-note"); status.setAttribute("role", "status"); section.append(status);
    const geometry = results.map((r) => routeGeometry(r, decode));
    const project = sharedProjection([...results[0].stops, ...geometry.flatMap((routes) => routes.flatMap((g) => [...g.overview, ...g.legs.flat()]))]);
    const grid = el("div", undefined, "comparison-map-grid"), cards = [];
    results.forEach((result, index) => {
      const card = el("article", undefined, "card comparison-map-card"), title = label(result.report.solver_name);
      card.append(el("p", `${result.report.objective_value.toLocaleString()} ${result.report.objective_units} · ${result.report.wall_time_ms.toFixed(2)} ms`, "eyebrow"), el("h3", title));
      const claim = el("span", result.report.status === "PROVEN_OPTIMAL_TSP" ? "Proven optimal" : result.feasible ? "Feasible · not proven optimal" : "Not fully feasible", "source-pill"); card.append(claim);
      const map = svgEl("svg", { viewBox: "0 0 600 400", role: "img", class: "comparison-map" });
      const legText = el("p", undefined, "comparison-leg"), progressText = el("p", undefined, "metric-copy");
      card.append(map, legText, progressText);
      const details = el("details"), summary = el("summary", "Visit order & route details"); details.append(summary);
      for (const route of result.routes) details.append(el("p", `Vehicle ${route.vehicle_id}: ${route.nodes.map(nodeLabel).join(" → ")}`, "comparison-sequence"));
      if (index) { const same = overlap(results[0], result); details.append(el("p", `${same.shared} of ${same.total} Greedy directed stop-to-stop edges also occur in this tour. This is not road-segment overlap.`, "metric-copy")); }
      for (const warning of result.warnings) details.append(el("p", warning, "error"));
      const open = el("button", "Open in route explorer ↗", "secondary"); open.type = "button"; open.addEventListener("click", () => onOpen(index));
      card.append(details, open); grid.append(card); cards.push({ map, legText, progressText, result, index, title });
    });
    for (const skip of skipped) { const card = el("article", undefined, "card comparison-map-card comparison-skipped"); card.append(el("p", "Not run", "eyebrow"), el("h3", label(skip.solver)), el("p", skip.reason, "metric-copy")); grid.append(card); }
    section.append(grid, el("p", results[0].provenance.geometry_kind === "road" ? "Shared geographic scale · actual OSRM road paths where available. Points show submitted coordinates; road snapping may differ. Selected leg is bold with a direction arrow." : "Shared geographic scale · dashed geographic estimates, not roads or traffic. Selected leg is bold with a direction arrow.", "metric-copy"));
    container.append(section);

    function paint() {
      const step = Number(range.value), departure = depart.value === "step" ? null : Number(depart.value);
      range.disabled = prev.disabled = next.disabled = departure !== null;
      if (departure === null) { prev.disabled = step === 0; next.disabled = step === Number(range.max); }
      output.textContent = `${step + 1} / ${Number(range.max) + 1}`;
      range.setAttribute("aria-valuetext", `Leg ${step + 1} of ${Number(range.max) + 1}`);
      const selected = results.map((r) => selectEdge(r, step, departure));
      status.textContent = `${departure === null ? `Visit step ${step + 1}` : `Departing from ${nodeLabel(departure)} · ${stopName(departure)}`}: ${selected.map((edge, i) => `${label(results[i].report.solver_name)} ${edge ? `${nodeLabel(edge.from)} → ${nodeLabel(edge.to)}` : "no served edge"}`).join(" · ")}`;
      cards.forEach(({ map, legText, progressText, result, index, title }) => {
        map.replaceChildren();
        const edge = selected[index], visited = new Set(edge ? result.routes[edge.routeIndex].sequence.slice(0, edge.leg) : []), markerId = `comparison-arrow-${index}`;
        const defs = svgEl("defs", {}), arrow = svgEl("marker", { id: markerId, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 5, markerHeight: 5, orient: "auto-start-reverse" }); arrow.append(svgEl("path", { d: "M0 0L10 5L0 10Z", fill: "#2d6051" })); defs.append(arrow); map.append(defs);
        const path = (points, active) => svgEl("polyline", { points: points.map((p) => project(p).join(",")).join(" "), fill: "none", stroke: "#2d6051", "stroke-width": active ? 3 : 1.5, opacity: active ? 1 : .18, "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": result.provenance.geometry_kind === "road" ? "none" : "7 5", ...(active ? { "marker-end": `url(#${markerId})` } : {}) });
        if (full.checked) for (const route of geometry[index]) if (route.overview.length) map.append(path(route.overview, false));
        const activePoints = edge ? geometry[index][edge.routeIndex].legs[edge.leg] || [] : [];
        if (activePoints.length) map.append(path(activePoints, true));
        result.stops.forEach((p, node) => {
          const [x, y] = project(p), active = edge && (node === edge.from || node === edge.to);
          const marker = svgEl("circle", { cx: x, cy: y, r: !node ? 8 : active ? 6 : 3.5, fill: active || visited.has(node) ? "#2d6051" : "#b5c2b8", stroke: "#fff", "stroke-width": 1.5 });
          marker.append(svgEl("title", {}, `${nodeLabel(node)} · ${stopName(node)}`)); map.append(marker);
          if (!node || active || names.checked) map.append(svgEl("text", { x: x + 10, y: y - 10, class: "map-node-label", "font-size": 14 }, nodeLabel(node)));
        });
        legText.textContent = edge ? `${nodeLabel(edge.from)} → ${nodeLabel(edge.to)} · ${edge.cost.toLocaleString()} ${result.matrix_metadata.unit}` : "No served edge for this selection.";
        const served = new Set(result.routes.flatMap((r) => r.sequence)).size;
        progressText.textContent = `Coverage ${served} / ${result.stops.length - 1} customers · ${result.unserved.length} unserved${edge ? ` · ${edge.leg} visits before this leg` : ""}${edge && !activePoints.length ? " · Road geometry unavailable for this leg" : ""}`;
        map.setAttribute("aria-label", `${title}. ${legText.textContent} ${progressText.textContent}`);
      });
    }
    range.addEventListener("input", paint); depart.addEventListener("change", paint); full.addEventListener("change", paint); names.addEventListener("change", paint);
    prev.addEventListener("click", () => { range.value = Math.max(0, Number(range.value) - 1); paint(); });
    next.addEventListener("click", () => { range.value = Math.min(Number(range.max), Number(range.value) + 1); paint(); });
    paint();
  }
  const api = { edges, selectEdge, overlap, sharedProjection, routeGeometry, mount };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.WaybillComparison = api;
}());
