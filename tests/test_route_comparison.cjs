"use strict";
const assert = require("node:assert/strict");
const { edges, selectEdge, overlap, sharedProjection, routeGeometry } = require("../web/route-comparison.js");
// Deliberate test doubles for display inspection, never shipped as solver results.
const a = { stops: [{ lat: 1, lon: 1 }, { lat: 1.1, lon: 1 }, { lat: 1.1, lon: 1.1 }, { lat: 1, lon: 1.1 }], routes: [{ nodes: [0, 1, 3, 2, 0], sequence: [1, 3, 2] }], matrix: [[0, 10, 20, 30], [11, 0, 12, 13], [21, 22, 0, 23], [31, 32, 33, 0]], provenance: { geometry_kind: "straight_line_estimate" } };
const b = { ...a, routes: [{ nodes: [0, 1, 2, 3, 0], sequence: [1, 2, 3] }] };
assert.equal(edges(a).length, 4);
assert.deepEqual(selectEdge(a, 1), { routeIndex: 0, leg: 1, from: 1, to: 3, cost: 13 });
assert.equal(selectEdge(b, 1).to, 2);
assert.equal(selectEdge(a, 0, 2).to, 0);
assert.equal(selectEdge(a, 3).to, 0); // Final depot-return leg is not dropped.
assert.equal(selectEdge(a, 4), null);
assert.equal(selectEdge(a, 0, 99), null);
assert.deepEqual(overlap(a, b), { shared: 1, total: 4 }); // Opposite directed edges do not match.
assert.deepEqual(overlap(a, a), { shared: 4, total: 4 });
const project = sharedProjection(a.stops);
for (const p of a.stops) assert.ok(project(p).every(Number.isFinite));
assert.deepEqual(project(a.stops[1]), project(b.stops[1])); // Same scale and orientation.
assert.ok(project(a.stops[1])[1] < project(a.stops[0])[1]); // North is up.
const collapsed = sharedProjection([{ lat: 0, lon: 0 }]);
assert.deepEqual(collapsed({ lat: 0, lon: 0 }), [300, 200]);
const offline = routeGeometry(a, () => { throw new Error("Offline data must not decode roads"); });
assert.deepEqual(offline[0].legs[1], [a.stops[1], a.stops[3]]);
const missing = routeGeometry({ ...a, provenance: { geometry_kind: "road" } }, () => []);
assert.deepEqual(missing, [{ overview: [], legs: [] }]); // No fabricated straight roads.
const road = routeGeometry({ ...a, provenance: { geometry_kind: "road" }, routes: [{ ...a.routes[0], geometry: { polyline: "overview", leg_polylines: [["first", "second"]] } }] }, (text) => [{ lat: text.length, lon: 1 }]);
assert.equal(road[0].overview.length, 1);
assert.equal(road[0].legs[0].length, 2);
const fleet = { ...a, routes: [{ nodes: [0, 1, 0], sequence: [1] }, { nodes: [0, 2, 3, 0], sequence: [2, 3] }] };
assert.deepEqual(selectEdge(fleet, 2), { routeIndex: 1, leg: 0, from: 0, to: 2, cost: 20 });
assert.equal(selectEdge({ ...a, routes: [] }, 0), null);
console.log("Route comparison display checks passed");
