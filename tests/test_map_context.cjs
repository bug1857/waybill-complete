'use strict';
const assert = require('node:assert/strict');
const { world, projection, tilePlan } = require('../web/map-context.js');
assert.deepEqual(world({lat:0, lon:0}), [128, 128]);
for (const lat of [-90, -85, 0, 85, 90]) assert.ok(world({lat, lon:0}).every(Number.isFinite));
assert.throws(() => projection([]));
assert.throws(() => projection([{lat:NaN,lon:0}]));
const points = [{lat:26.9124,lon:75.7873}, {lat:26.9239299,lon:75.8268692}];
const p = projection(points);
assert.ok(p.project(points[1])[1] < p.project(points[0])[1]);
for (const view of [[0,0,900,550], [200,100,200,120], [-5000,-5000,10000,8000]]) {
  const tiles = tilePlan(p, view, 1200);
  assert.ok(tiles.length > 0 && tiles.length <= 48);
  assert.equal(new Set(tiles.map(t => t.key)).size, tiles.length);
  for (const tile of tiles) {
    const [z,x,y] = tile.key.split('/').map(Number);
    assert.ok(z >= 0 && z <= 19 && x >= 0 && x < 2**z && y >= 0 && y < 2**z);
    assert.ok([tile.x,tile.y,tile.size].every(Number.isFinite));
    const worldX = (tile.x - p.x) / p.scale;
    assert.ok(Math.abs(worldX - x * 256 / 2**z) < 1e-8);
  }
}
assert.deepEqual(tilePlan(p, [0,0,900,550], 0), []);
assert.deepEqual(projection([{lat:0,lon:0}], 600,400,50).project({lat:0,lon:0}), [300,200]);
console.log('Map context: projection alignment, polar bounds and viewport-only tile cap passed');
