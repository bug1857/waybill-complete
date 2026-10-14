"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../web/live.js"), "utf8");
const placesSource = fs.readFileSync(path.join(__dirname, "../web/real-data.js"), "utf8");
const fileNodes = new Map();
const makeNode = () => ({ value: "", disabled: false, children: [], listeners: {},
  replaceChildren(...children) { this.children = children; }, append(...children) { this.children.push(...children); },
  addEventListener(type, handler) { this.listeners[type] = handler; }, setAttribute() {}, focus() {} });
const fileNode = id => { if (!fileNodes.has(id)) fileNodes.set(id, makeNode()); return fileNodes.get(id); };
let fileRequests = 0;
vm.runInNewContext(placesSource, { location: {protocol:"file:"}, fetch() { fileRequests++; throw new Error("file mode must not fetch"); },
  document: {getElementById:fileNode, createElement:makeNode, createTextNode:text=>({textContent:text})} });
assert.equal(fileRequests, 0);
assert.equal(fileNode("custom-search").disabled, true);
assert.equal(fileNode("custom-query").disabled, true);
assert.ok(fileNode("custom-coverage").textContent.includes("none loaded"));
assert.equal(fileNode("custom-search-error").children[1].href, "http://127.0.0.1:8000/live.html#real-data");
for (let i=0;i<2;i++) {
  fileNode("custom-name").value = `Offline test ${i}`; fileNode("custom-lat").value = String(i); fileNode("custom-lon").value = "0";
  fileNode("custom-manual-form").listeners.submit({preventDefault() {}});
}
assert.equal(fileNode("custom-stops").children.length, 2);
assert.equal(fileNode("use-custom-places").disabled, true);
fileNode("custom-stops").children[1].children[1].children[1].listeners.click();
assert.equal(fileNode("custom-stops").children.length, 1);
assert.equal(fileNode("custom-error").textContent, "");
fileNode("custom-search-form").listeners.submit({preventDefault() {}});
fileNode("places-form").listeners.submit({preventDefault() {}});
assert.equal(fileRequests, 0);
const ctx = vm.createContext({ byId: () => ({ value: "" }) });
// Follow the existing display test's pattern: exercise the actual page functions.
vm.runInContext(source.slice(source.indexOf("  function parseStops("), source.indexOf("  function payloadFromForm(")), ctx);
vm.runInContext(source.slice(source.indexOf("  function parseImport("), source.indexOf("  function loadDataset(")), ctx);
const parse = (data) => ctx.parseImport(JSON.stringify(data), true, "haversine");
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures/import-config.json"), "utf8"));
const result = parse(fixture);
assert.equal(result.solver, "held_karp"); assert.equal(result.wall_time_ms, 250);
assert.equal(result.stops.length, 3); assert.equal(result.provider, "haversine");
const csv = ctx.parseImport("latitude,longitude\n43.7,7.4\n43.71,7.41", false, "haversine");
assert.equal(csv.stops.length, 2);
assert.equal(ctx.parseImport(fs.readFileSync(path.join(__dirname, "fixtures/import-valid.csv"), "utf8"), false, "haversine").stops.length, 3);
assert.throws(() => ctx.parseImport(fs.readFileSync(path.join(__dirname, "fixtures/import-invalid.csv"), "utf8"), false, "haversine"));
assert.throws(() => ctx.parseImport("43.7,\n43.71,7.41", false, "haversine"));
assert.throws(() => ctx.parseImport("nonsense,columns\n43.7,7.4\n43.71,7.41", false, "haversine"));
for (const change of [{ stops: [null, {}] }, { stops: [{ lat: 91, lon: 0 }, { lat: 0, lon: 0 }] }, { solver: "fake" }, { wall_time_ms: 2001 }, { wall_time_ms: null }, { vehicles: 2 }, { problem: "other" }, { provider: "remote" }, { dataset: 1 }, { places: [null, null, null] }]) assert.throws(() => parse({ ...fixture, ...change }));
const fleet = parse({ problem: "CVRPTW", stops: [{ lat: 43.7, lon: 7.4 }, { lat: 43.71, lon: 7.41, demand: 2 }] });
assert.equal(fleet.stops[1].latest, 28800); assert.equal(fleet.stops[1].service_time, 120);
assert.equal(fleet.solver, "savings");
assert.equal(parse({ stops: [{ lat: 0, lon: 0 }, { lat: .1, lon: .1, earliest: 1, latest: 20 }] }).problem, "CVRPTW");
assert.throws(() => parse({ problem: "CVRPTW", stops: [{ lat: 0, lon: 0 }, { lat: .1, lon: .1, earliest: 20, latest: 10 }] }));
const named = { ...fixture, places: fixture.stops.map((s, i) => ({ ...s, name: `Test place ${i}` })), provenance: { source: "Test-only metadata" } };
assert.equal(parse(named).places[1].name, "Test place 1");
assert.throws(() => parse({ ...named, places: named.places.toReversed() }));
const { buildCustomDataset } = require('../web/real-data.js');
const largeCustom = buildCustomDataset(Array.from({length:100}, (_,i)=>({name:'अ'.repeat(240),lat:0,lon:i,query:'अ'.repeat(200),source:'OpenStreetMap via Photon',retrieved_at:'2026-10-13T00:00:00Z',response_sha256:'a'.repeat(64),coordinate_kind:'mapped search result'})));
// Export input includes the API fields and dataset metadata, not duplicate top-level places.
const exportedInput = JSON.stringify({stops:largeCustom.stops,problem:'TSP',provider:'haversine',dataset:largeCustom}, null, 2);
assert.ok(Buffer.byteLength(exportedInput) <= 262144);
assert.ok(Buffer.byteLength(exportedInput) > 65536); // Long UTF-8 place metadata exceeds the previous import cap.
assert.equal(parse(JSON.parse(exportedInput)).places.length, 100);

// Importing or switching datasets restores every control, including a custom budget.
const nodes = Object.fromEntries(["problem", "solver", "provider", "vehicles", "capacity", "shift", "budget", "stops", "hero-title", "import-error"].map(id => [id, { value: "", options: [], append(option) { this.options.push(option); } }]));
let edits = 0;
const controls = vm.createContext({ byId: id => nodes[id], chooseModel() {}, element: () => ({}), inputEdited() { edits++; } });
vm.runInContext(source.slice(source.indexOf("  function loadDataset("), source.indexOf("  async function importFile(")), controls);
controls.loadDataset({ ...result, wall_time_ms: 777 });
assert.equal(nodes.solver.value, "held_karp"); assert.equal(nodes.budget.value, 777);
assert.equal(nodes.budget.options.length, 1); assert.equal(edits, 1);
controls.loadDataset(fleet);
assert.equal(nodes.problem.value, "CVRPTW"); assert.equal(nodes.solver.value, "savings");
assert.ok(nodes.stops.value.includes("2, 0, 28800, 120"));

(async () => {
  const importer = vm.createContext({});
  vm.runInContext(source.slice(source.indexOf("  async function importFile("), source.indexOf('  document.addEventListener("waybill:dataset"')), importer);
  await assert.rejects(importer.importFile({ size: 262145, text() { throw new Error("oversized files must not be read"); } }), /256 KB/);
  const http = vm.createContext({ AbortSignal, fetch: async () => ({ status: 503, json: async () => { throw new SyntaxError("HTML maintenance page"); } }) });
  vm.runInContext(source.slice(source.indexOf("  async function request("), source.indexOf("  function setBusy(")), http);
  await assert.rejects(http.request("/api/solve"), /unreadable response \(HTTP 503\)/);
  let deliver;
  const pending = new Promise(resolve => { deliver = resolve; });
  const stale = vm.createContext({ inputRevision: 0, request: () => pending });
  vm.runInContext(source.slice(source.indexOf("  async function solve("), source.indexOf("  function svgElement(")), stale);
  const solve = stale.solve({}); stale.inputRevision++; deliver({});
  await assert.rejects(solve, /Inputs changed while calculating/);
  assert.ok(source.includes("revision !== inputRevision || JSON.stringify(payloadFromForm())"));
  assert.ok(source.includes('window.addEventListener("hashchange"'));
  console.log("Live UI: import validation, settings restoration and stale-response guards passed");
})().catch(error => { console.error(error); process.exitCode = 1; });
