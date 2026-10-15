/* Display coordinates only. Never changes the solver's stops, matrix or distances. */
(function () {
  "use strict";
  const ns = "http://www.w3.org/2000/svg";
  function world(point) {
    const lat = Math.max(-85.05112878, Math.min(85.05112878, point.lat)) * Math.PI / 180;
    return [(point.lon + 180) / 360 * 256, (1 - Math.asinh(Math.tan(lat)) / Math.PI) * 128];
  }
  function projection(points, width = 900, height = 550, padding = 60) {
    if (!points.length || points.some(p => !Number.isFinite(p.lat) || !Number.isFinite(p.lon))) throw new Error("Map needs finite coordinates.");
    const bounds = points.map(world).reduce((b, [x, y]) => [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)], [Infinity, Infinity, -Infinity, -Infinity]);
    const scale = Math.min((width - 2 * padding) / Math.max(bounds[2] - bounds[0], .00001), (height - 2 * padding) / Math.max(bounds[3] - bounds[1], .00001));
    const x = width / 2 - (bounds[0] + bounds[2]) / 2 * scale, y = height / 2 - (bounds[1] + bounds[3]) / 2 * scale;
    return { scale, x, y, project: p => { const [wx, wy] = world(p); return [wx * scale + x, wy * scale + y]; } };
  }
  function tilePlan(p, view, pixelWidth) {
    if (!(pixelWidth > 0) || !view.every(Number.isFinite) || view[2] <= 0 || view[3] <= 0) return [];
    let z = Math.max(0, Math.min(19, Math.floor(Math.log2(p.scale * pixelWidth / view[2]))));
    let bounds;
    do {
      const n = 2 ** z, size = 256 / n;
      bounds = [Math.max(0, Math.floor((view[0] - p.x) / p.scale / size)), Math.max(0, Math.floor((view[1] - p.y) / p.scale / size)), Math.min(n - 1, Math.floor((view[0] + view[2] - p.x) / p.scale / size)), Math.min(n - 1, Math.floor((view[1] + view[3] - p.y) / p.scale / size))];
      if ((bounds[2] - bounds[0] + 1) * (bounds[3] - bounds[1] + 1) <= 48 || !z) break;
      z--;
    } while (z >= 0);
    const tiles = [], size = 256 / 2 ** z * p.scale;
    for (let x = bounds[0]; x <= bounds[2]; x++) for (let y = bounds[1]; y <= bounds[3]; y++) tiles.push({ key: `${z}/${x}/${y}`, x: p.x + x * size, y: p.y + y * size, size });
    return tiles;
  }
  function svgNode(tag, attrs, text) {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function drawTiles(svg, p, view, enabled, status) {
    let group = svg.querySelector(".street-tiles");
    if (!enabled) { group?.remove(); if (status) status.textContent = "Street background off. Enabling sends the viewed map area to tile.openstreetmap.org; keep off for confidential locations. Routes work independently."; return; }
    const width = svg.getBoundingClientRect().width;
    if (!width || svg.closest("[hidden]")) return;
    if (!group) { group = svgNode("g", { class: "street-tiles", "aria-hidden": "true" }); svg.insertBefore(group, svg.firstChild); }
    const tiles = tilePlan(p, view, width), keys = new Set(tiles.map(t => t.key));
    for (const image of [...group.children]) if (!keys.has(image.dataset.tile)) image.remove();
    const present = new Set([...group.children].map(image => image.dataset.tile));
    if (status) status.textContent = group.dataset.failed ? "Some street tiles are unavailable. Calculated routes still work; turn the background off for a clear view." : "OpenStreetMap street background · viewport area is sent to tile.openstreetmap.org. No traffic data.";
    for (const tile of tiles) if (!present.has(tile.key)) {
      const image = svgNode("image", { x: tile.x, y: tile.y, width: tile.size, height: tile.size, href: `https://tile.openstreetmap.org/${tile.key}.png`, preserveAspectRatio: "none", "data-tile": tile.key });
      image.addEventListener("error", () => { group.dataset.failed = "true"; if (group.isConnected && status) status.textContent = "Some street tiles are unavailable. Calculated routes still work; turn the background off for a clear view."; });
      group.append(image);
    }
  }
  function coverage(svg, region, queryBox, stops) {
    svg.replaceChildren();
    const [south, west, north, east] = region.bbox;
    const p = projection([{ lat: south, lon: west }, { lat: north, lon: east }], 600, 340, 40);
    function box(bounds, cls) {
      const [s, w, n, e] = bounds, [x, y] = p.project({ lat: n, lon: w }), [right, bottom] = p.project({ lat: s, lon: e });
      return svgNode("rect", { x, y, width: right - x, height: bottom - y, class: cls });
    }
    svg.append(box(region.bbox, "coverage-boundary"));
    const sharedBounds = queryBox?.every((value, i) => value === region.bbox[i]);
    if (queryBox && !sharedBounds) svg.append(box(queryBox, "coverage-query"));
    if (sharedBounds) svg.append(svgNode("text", { x: 14, y: 46, class: "coverage-coordinate" }, "Road and query boundaries coincide · shown once"));
    let outside = 0;
    stops.forEach((stop, i) => {
      if (stop.lat < south || stop.lat > north || stop.lon < west || stop.lon > east) { outside++; return; }
      const [cx, cy] = p.project(stop), marker = svgNode("circle", { cx, cy, r: i ? 4 : 7, class: "coverage-stop" });
      marker.append(svgNode("title", {}, `${i ? `Stop ${i}` : "Start / return"} · ${stop.name}`)); svg.append(marker);
    });
    svg.append(svgNode("text", { x: 14, y: 24, class: "coverage-coordinate" }, "N ↑"), svgNode("text", { x: 14, y: 326, class: "coverage-coordinate" }, `${south}–${north}° N · ${west}–${east}° E${outside ? ` · ${outside} stops outside this area` : ""}`));
    svg.setAttribute("aria-label", `${region.name}. Road-routing boundary: latitude ${south} to ${north}, longitude ${west} to ${east}. ${outside} submitted stops outside this area.`);
  }
  const api = { world, projection, tilePlan, drawTiles, coverage };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.WaybillMap = api;
}());
