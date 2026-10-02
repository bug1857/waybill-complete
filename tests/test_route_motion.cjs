/* Run: node tests/test_route_motion.cjs */
const assert = require('node:assert/strict');
const { decodePolyline, buildTrack, position, fitView, distanceAtProgress, progressAtDistance, turnAngle, heading } = require('../web/route-motion.js');
assert.deepEqual(decodePolyline('_p~iF~ps|U_ulLnnqC_mqNvxq`@'), [{lat:38.5,lon:-120.2},{lat:40.7,lon:-120.95},{lat:43.252,lon:-126.453}]);
assert.throws(() => decodePolyline('_'));
const track = buildTrack([[[0,0],[3,0],[3,4]], [[3,4],[0,0]]]);
const halfway = position(track, .5);
assert.equal(halfway.x, 3); assert.equal(halfway.y, .5); assert.equal(halfway.completed, 0);
assert.deepEqual(position(track, 1), {x:3,y:4,angle:Math.atan2(-4,-3)*180/Math.PI,leg:1,completed:1});
assert.equal(position(track, 2).completed, 2); assert.equal(position(track, 2).x, 0);
assert.equal(position(track, -1).completed, 0); assert.equal(position(track, 99).completed, 2);
const duplicate = buildTrack([[[5,5],[5,5]], [[5,5]]]);
assert.equal(position(duplicate, .5).x, 5); assert.equal(position(duplicate, 2).y, 5);
assert.throws(() => buildTrack([[]]));
const fitted = fitView([[258,92],[582,421]], 1.3, 32);
assert.equal(fitted[2] / fitted[3], 1.3);
assert.ok(fitted[2] < 900);
for (const [x,y] of [[258,92],[582,421]]) assert.ok(x >= fitted[0] && x <= fitted[0]+fitted[2] && y >= fitted[1] && y <= fitted[1]+fitted[3]);
assert.ok(fitView([[5,5],[5,5]], 1)[2] > 0);
assert.deepEqual(fitView([], 1), [0,0,900,550]);
console.log('Route motion: geometry decoding, per-leg interpolation, visit boundaries and zero-length legs passed.');

// A comparison renders the planner while hidden. Zero width must not enlarge markers.
const source = require('node:fs').readFileSync(require('node:path').join(__dirname, '../web/live.js'), 'utf8');
const mapViewCode = source.slice(source.indexOf('  function setMapView('), source.indexOf('  function fitMap('));
let width = 0, writes = [];
const marker = {dataset:{node:'1'},setAttribute:(name,value)=>writes.push([name,value])};
const map = {getBoundingClientRect:()=>({width}), setAttribute:(name,value)=>writes.push([name,value]),
  querySelectorAll:selector=>selector==='.map-node' ? [marker] : []};
const context = {byId:()=>map, playback:null, mapScale:0};
require('node:vm').runInNewContext(mapViewCode+'setMapView([0,0,900,550]);', context);
assert.deepEqual(writes, []);
width = 450;
require('node:vm').runInNewContext(mapViewCode+'setMapView([0,0,900,550]);', context);
assert.deepEqual(writes.at(-1), ['r',8]);
assert.ok(source.includes('new ResizeObserver('));
console.log('Hidden-panel map scale: deferred at zero width, correctly fitted when visible.');

const unequal = buildTrack([[[0,0],[10,0]], [[10,0],[110,0]]]);
assert.equal(progressAtDistance(unequal, 10), 1);
assert.ok(Math.abs(position(unequal, progressAtDistance(unequal, 20)).x - 20) < 1e-9);
assert.equal(distanceAtProgress(unequal, 1.5), 60);
assert.equal(progressAtDistance(unequal, 999), 2);
assert.equal(progressAtDistance(duplicate, 1), 2);
assert.equal(heading(unequal, 1), 0);
assert.ok(turnAngle(179, -179, 16) > 179); // cross the seam by 2 degrees, not 358
assert.ok(turnAngle(-179, 179, 16) < -179);
assert.equal(turnAngle(90, -90, 0), 90);
const one = turnAngle(0, 90, 32), two = turnAngle(turnAngle(0, 90, 16), 90, 16);
assert.ok(Math.abs(one - two) < 1e-9); // frame-rate independent turn smoothing
console.log('Smooth motion: distance-paced unequal legs, heading seams, time-based interpolation passed.');

const { buildDataset } = require('../web/real-data.js');
const catalog = {regionName:'Test-only region', categoryName:'Test-only category', roads:false, provenance:{response_sha256:'a'.repeat(64)}, places:[
  {lat:0,lon:0,name:'Fixture depot',osm_id:1}, {lat:0,lon:.02,name:'Fixture far',osm_id:2}, {lat:0,lon:.01,name:'Fixture near',osm_id:3}]};
const data = buildDataset(catalog, {depot:0,count:2,model:'TSP'});
assert.deepEqual(data.places.map(p=>p.osm_id), [1,3,2]);
assert.equal(data.provider, 'haversine'); assert.equal(data.stops.length, 3);
assert.equal(data.provenance.response_sha256, catalog.provenance.response_sha256);
assert.throws(()=>buildDataset(catalog,{depot:0,count:3,model:'TSP'}));
const fleetData = buildDataset({...catalog,roads:true}, {depot:0,count:1,model:'CVRPTW',vehicles:2,capacity:10,demand:2,service:120,shift:28800});
assert.equal(fleetData.provider, 'osrm'); assert.equal(fleetData.solver, 'savings');
assert.deepEqual(fleetData.stops[0], {lat:0,lon:0});
assert.equal(fleetData.stops[1].demand, 2); assert.equal(fleetData.stops[1].latest, 28800);
console.log('Real-data builder: fetched identities, honest selection limits, user-defined fleet constraints passed.');
