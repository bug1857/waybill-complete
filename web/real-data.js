/* Fetched locations + explicitly chosen assumptions. No route solver lives here. */
(function () {
  "use strict";
  function buildDataset(catalog, answers) {
    const places = catalog.places, depot = places[answers.depot];
    if (!depot || !Number.isInteger(answers.count) || answers.count < 1 || answers.count > 99 || answers.count >= places.length) throw new Error("Choose a depot and an available number of customer stops.");
    if (!["TSP", "CVRPTW"].includes(answers.model)) throw new Error("Choose a supported planning model.");
    const fleet = answers.model === "CVRPTW";
    for (const [key, min, max] of [["vehicles", 1, 6], ["capacity", 1, 100000], ["demand", 1, 100000], ["service", 0, 86400], ["shift", 1, 86400]]) {
      if (fleet && (!Number.isInteger(answers[key]) || answers[key] < min || answers[key] > max)) throw new Error(`Invalid ${key} constraint.`);
    }
    const scale = Math.cos(depot.lat * Math.PI / 180);
    const proximity = (p) => Math.hypot(p.lat - depot.lat, (p.lon - depot.lon) * scale);
    const chosen = [depot, ...places.filter((p) => p !== depot).sort((a, b) => proximity(a) - proximity(b) || a.osm_id - b.osm_id).slice(0, answers.count)];
    const stops = chosen.map((p, i) => ({ lat: p.lat, lon: p.lon, ...(fleet && i ? { demand: answers.demand, earliest: 0, latest: answers.shift, service_time: answers.service } : {}) }));
    return { name: `${catalog.regionName} · ${catalog.categoryName} · real places`, stops, places: chosen,
      problem: answers.model, solver: fleet ? "savings" : "nearest_neighbor", provider: catalog.roads ? "osrm" : "haversine",
      vehicles: fleet ? answers.vehicles : 1, capacity: fleet ? answers.capacity : 25, shift_end: fleet ? answers.shift : 28800, wall_time_ms: 1000,
      provenance: { ...catalog.provenance, selection: "geographic proximity to user-selected depot", planning_assumptions: fleet ? { parcels_per_customer: answers.demand, service_seconds: answers.service, shift_seconds: answers.shift, windows: "entire user-defined shift" } : { model: "TSP", actual_orders: false } } };
  }
  function validateCustomPlaces(places) {
    if (!Array.isArray(places) || places.length < 1 || places.length > 100) throw new Error("Use at most 100 places, including the starting depot.");
    const seen = new Set();
    for (const p of places) {
      if (!p || typeof p.name !== "string" || !p.name.trim() || p.name.length > 240 || !Number.isFinite(p.lat) || !Number.isFinite(p.lon) || Math.abs(p.lat) > 90 || Math.abs(p.lon) > 180) throw new Error("Each place needs a name and valid latitude / longitude.");
      const key = `${p.lat},${p.lon}`;
      if (seen.has(key)) throw new Error("This location is already in your stop list.");
      seen.add(key);
    }
  }
  function buildCustomDataset(places) {
    validateCustomPlaces(places);
    if (places.length < 2) throw new Error("Add a starting place and 1–99 delivery stops.");
    return { name: `Custom round trip · ${places[0].name}`, places: places.map(p => ({ ...p })), stops: places.map(({ lat, lon }) => ({ lat, lon })),
      problem: "TSP", solver: "nearest_neighbor", provider: "haversine", vehicles: 1, capacity: 25, shift_end: 28800, wall_time_ms: 1000,
      provenance: { source: "User-selected custom places", selection: "first place is the start and return depot; remaining stops are optimized", locations_only: true,
        attribution: "Search results: © OpenStreetMap contributors · ODbL; manual coordinates are user supplied", planning_assumptions: { model: "TSP", actual_orders: false } } };
  }
  if (typeof module !== "undefined") { module.exports = { buildDataset, buildCustomDataset }; return; }
  const byId = (id) => document.getElementById(id);
  const fileMode = location.protocol === "file:";
  let options = null, catalog = null;
  const fields = byId("real-build-fields"), preview = byId("places-preview"), button = byId("fetch-places");
  function node(tag, text, cls) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; }
  const selectedPlaces = [];
  function renderCustomStops() {
    const list = byId("custom-stops"); list.replaceChildren();
    byId("custom-error").textContent = "";
    byId("custom-summary").textContent = selectedPlaces.length ? `${selectedPlaces.length} places · start and return: ${selectedPlaces[0].name}` : "Add your starting place, then the places you want to visit.";
    byId("use-custom-places").disabled = fileMode || selectedPlaces.length < 2;
    selectedPlaces.forEach((p, i) => {
      const row = node("article", undefined, "place-row"), info = node("div");
      info.append(node("strong", `${i ? `Stop ${i}` : "Start / return"} · ${p.name}`), node("small", `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)} · ${p.coordinate_kind}`));
      const actions = node("div", undefined, "custom-stop-actions");
      if (i) {
        const start = node("button", "Start here", "secondary small-button"); start.type = "button"; start.setAttribute("aria-label", `Start and return at ${p.name}`);
        start.addEventListener("click", () => { selectedPlaces.unshift(selectedPlaces.splice(i, 1)[0]); renderCustomStops(); byId("use-custom-places").focus(); }); actions.append(start);
      }
      const remove = node("button", "Remove", "secondary small-button"); remove.type = "button"; remove.setAttribute("aria-label", `Remove ${p.name}`);
      remove.addEventListener("click", () => { selectedPlaces.splice(i, 1); renderCustomStops(); byId("custom-query").focus(); }); actions.append(remove);
      row.append(info, actions); list.append(row);
    });
  }
  function addCustomPlace(place) {
    byId("custom-error").textContent = "";
    try {
      validateCustomPlaces([...selectedPlaces, place]);
      selectedPlaces.push({ ...place }); renderCustomStops();
      byId("custom-error").textContent = `${place.name} added.`;
    } catch (e) { byId("custom-error").textContent = e.message; }
  }
  byId("custom-manual-form").addEventListener("submit", event => {
    event.preventDefault();
    addCustomPlace({ name: byId("custom-name").value.trim(), lat: Number(byId("custom-lat").value), lon: Number(byId("custom-lon").value), coordinate_kind: "user-supplied coordinates", source: "Manual entry" });
  });
  byId("custom-search-form").addEventListener("submit", async event => {
    event.preventDefault(); if (fileMode) return;
    const button = byId("custom-search"), results = byId("custom-results");
    button.disabled = true; button.textContent = "Searching…"; results.replaceChildren(); byId("custom-search-error").textContent = "";
    byId("custom-search-form").setAttribute("aria-busy", "true");
    try {
      const response = await fetch("/api/places/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: byId("custom-query").value }), signal: AbortSignal.timeout(20000) });
      let data;
      try { data = await response.json(); } catch (_) { throw new Error(`Place search returned an unreadable response (HTTP ${response.status}).`); }
      if (!response.ok) throw new Error(data.error || "Place search is unavailable.");
      if (!data.places.length) results.append(node("p", "No matching places. Include the city, try another name, or enter coordinates below.", "metric-copy"));
      data.places.forEach(p => {
        const row = node("article", undefined, "place-row"), info = node("div"), add = node("button", "Add stop", "secondary small-button");
        info.append(node("strong", p.name), node("small", `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`));
        add.type = "button"; add.setAttribute("aria-label", `Add ${p.name}`); add.addEventListener("click", () => addCustomPlace(p)); row.append(info, add); results.append(row);
      });
    } catch (e) { byId("custom-search-error").textContent = e.name === "TimeoutError" ? "Place search timed out. Retry or enter coordinates below." : e.message; }
    finally { button.disabled = false; button.textContent = "Search places"; byId("custom-search-form").setAttribute("aria-busy", "false"); }
  });
  byId("use-custom-places").addEventListener("click", () => {
    try { document.dispatchEvent(new CustomEvent("waybill:dataset", { detail: buildCustomDataset(selectedPlaces) })); } catch (e) { byId("custom-error").textContent = e.message; }
  });
  renderCustomStops();
  function answers() { return Object.fromEntries(["depot", "count", "model", "vehicles", "capacity", "demand", "service", "shift"].map((key) => [key, key === "model" ? byId(`real-${key}`).value : Number(byId(`real-${key}`).value)])); }
  function currentDataset() { if (!catalog) throw new Error("Fetch places first."); return buildDataset(catalog, answers()); }
  function renderPreview() {
    byId("real-fleet-fields").hidden = byId("real-model").value !== "CVRPTW";
    if (!catalog || fields.disabled) return;
    byId("dataset-error").textContent = "";
    try {
      const dataset = currentDataset(); preview.className = "places-preview"; preview.replaceChildren();
      const demand = dataset.stops.reduce((sum, stop) => sum + (stop.demand || 0), 0), capacity = dataset.vehicles * dataset.capacity;
      byId("real-plan-summary").textContent = dataset.problem === "TSP" ? `${dataset.stops.length} real-location nodes · one depot, ${dataset.stops.length - 1} customers · ${dataset.provider === "osrm" ? "road routing" : "distance estimates"}` : `${demand} user-assumed parcels · ${capacity} total fleet capacity${demand > capacity ? " · insufficient capacity: expect unserved stops" : " · feasibility still needs a canonical solve"}`;
      byId("preview-title").textContent = `${dataset.stops.length - 1} stops. One clear plan.`;
      dataset.places.forEach((p, i) => {
        const row = node("article", undefined, "place-row"), number = node("span", i ? String(i).padStart(2, "0") : "D", "place-number");
        const info = node("div"), link = node("a", p.name); link.href = p.url; link.target = "_blank"; link.rel = "noopener noreferrer";
        info.append(link, node("small", `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)} · ${p.coordinate_kind}`)); row.append(number, info); preview.append(row);
      });
      byId("places-source").textContent = JSON.stringify(dataset.provenance, null, 2);
    } catch (e) { byId("dataset-error").textContent = e.message; }
  }
  function invalidate() {
    catalog = null; fields.disabled = true; byId("places-provenance").hidden = true;
    byId("preview-title").textContent = "Your next journey."; byId("places-count").textContent = "No places yet";
    byId("places-status").textContent = "Selection changed. Fetch this area and category to build a dataset.";
    preview.className = "places-preview empty"; preview.replaceChildren(node("p", "Fetch places for your selected area."));
    byId("real-plan-summary").textContent = "";
    byId("places-error").textContent = ""; byId("dataset-error").textContent = "";
    const region = options?.regions[byId("real-region").value];
    byId("real-coverage").textContent = region?.roads ? "Monaco road coverage · OSRM road distances and geometry" : "Real Indian locations · geographic distance estimates (not road distances or live traffic)";
  }
  byId("real-region").addEventListener("change", invalidate); byId("real-category").addEventListener("change", invalidate);
  fields.addEventListener("change", renderPreview);
  byId("places-form").addEventListener("submit", async (event) => {
    event.preventDefault(); if (fileMode) return;
    invalidate(); button.disabled = true; button.textContent = "Fetching OpenStreetMap…";
    byId("real-region").disabled = true; byId("real-category").disabled = true;
    byId("places-loading").hidden = false; byId("places-form").setAttribute("aria-busy", "true");
    byId("places-status").textContent = "Fetching public map records. This can take up to 25 seconds.";
    try {
      const region = byId("real-region").value, category = byId("real-category").value;
      const response = await fetch("/api/places", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ region, category }), signal: AbortSignal.timeout(35000) });
      const data = await response.json(); if (!response.ok) throw new Error(data.error || "The public places service is unavailable.");
      catalog = { ...data, regionName: options.regions[region].name, categoryName: options.categories[category].name, roads: options.regions[region].roads };
      byId("places-count").textContent = `${data.places.length} found`;
      byId("places-status").textContent = `${data.cached ? "Cached public records" : "Fetched public records"} · retrieved ${new Date(data.provenance.retrieved_at).toLocaleString()} · ${data.places.length === 200 ? "query capped at 200 features" : "not an exhaustive business directory"}`;
      if (data.places.length < 2) throw new Error("Not enough mapped places in this area to form a tour. Try another category; no replacement locations will be invented.");
      const depot = byId("real-depot"); depot.replaceChildren();
      data.places.forEach((p, i) => { const option = node("option", p.name); option.value = i; depot.append(option); });
      const count = byId("real-count"), available = Math.min(99, data.places.length - 1);
      count.replaceChildren();
      const sizes = [...new Set([5, 10, 20, 50, 99, available].filter((n) => n <= available))].sort((a, b) => a - b);
      sizes.forEach((n) => { const option = node("option", `${n} customer stops`); option.value = n; count.append(option); });
      count.value = sizes.includes(10) ? "10" : sizes[0]; fields.disabled = false; byId("places-provenance").hidden = false; renderPreview();
    } catch (e) {
      byId("places-error").textContent = e.name === "TimeoutError" ? "The public data request timed out. Retry later; no fallback data was generated." : e.message;
      byId("places-status").textContent = "Dataset not created. Resolve the fetch error to continue.";
    } finally {
      button.disabled = false; button.textContent = "Fetch real places ↗"; byId("real-region").disabled = false; byId("real-category").disabled = false;
      byId("places-loading").hidden = true; byId("places-form").setAttribute("aria-busy", "false");
    }
  });
  byId("use-real-data").addEventListener("click", () => {
    try { document.dispatchEvent(new CustomEvent("waybill:dataset", { detail: currentDataset() })); } catch (e) { byId("dataset-error").textContent = e.message; }
  });
  byId("download-real-data").addEventListener("click", () => {
    try { document.dispatchEvent(new CustomEvent("waybill:download", { detail: { name: `waybill-${catalog.region}-${catalog.category}.json`, value: JSON.stringify(currentDataset(), null, 2) } })); } catch (e) { byId("dataset-error").textContent = e.message; }
  });
  if (fileMode) {
    const message = "This page was opened as a file. Search and routing need the local server. Run make live, then ";
    const link = node("a", "open the running app ↗"); link.href = "http://127.0.0.1:8000/live.html#real-data"; link.target = "_blank"; link.rel = "noopener";
    byId("custom-search-error").replaceChildren(document.createTextNode(message), link);
    byId("custom-query").disabled = true; byId("custom-search").disabled = true;
    byId("places-error").textContent = "Open the running app using the link above to fetch places.";
    byId("real-region").replaceChildren(node("option", "Open the running app first"));
    byId("real-category").replaceChildren(node("option", "Open the running app first"));
    return;
  }
  fetch("/api/places/options").then(async (response) => {
    if (!response.ok) throw new Error("Could not load the real-data setup. Reload when the engine is available.");
    options = await response.json();
    for (const [field, values] of [["real-region", options.regions], ["real-category", options.categories]]) {
      const select = byId(field); select.replaceChildren(); Object.entries(values).forEach(([key, value]) => { const option = node("option", value.name); option.value = key; select.append(option); }); select.disabled = false;
    }
    button.disabled = false; invalidate();
  }).catch((e) => { byId("places-error").textContent = e.message; });
}());
