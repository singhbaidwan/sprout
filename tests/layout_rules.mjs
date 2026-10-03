// Browser planning must agree with named destinations and fixed terrain.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync(new URL('../static/layout-rules.js',import.meta.url),'utf8');
const {layoutEntities, validatePositions, routeCosts, routeDistance, compactPositions} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const catalog = {
  entities:{chest:{x:0,y:6},mill:{x:3,y:6},oven:{x:6,y:6},depot:{x:7,y:3}},
  recycling:{entities:{well:{x:0,y:0},composter:{x:1,y:5},mixer:{x:5,y:5}}},
  obstacles:[[6,2],[6,3],[3,4]], field:{width:6,height:4},
  layout:{movable:['mill','oven','composter','mixer'],compact:{mill:{x:1,y:6},oven:{x:2,y:6},composter:{x:0,y:4},mixer:{x:1,y:4}}}
};
const original = JSON.stringify(catalog);
const campaign = {scenario:'factory'};
const compact = compactPositions(campaign,catalog);
assert.equal(validatePositions(campaign,catalog,compact),null);
assert.deepEqual(Object.keys(compact),['mill','oven']);
assert.deepEqual(routeCosts(campaign,catalog).map(r=>r.moves),[3,3,4]);
assert.deepEqual(routeCosts(campaign,catalog,compact).map(r=>r.moves),[1,1,8]);
assert.equal(routeDistance({x:5,y:3},{x:7,y:3},catalog),4);
assert.equal(routeDistance({x:1,y:6},{x:1,y:6},catalog),0);
assert.deepEqual(layoutEntities({...campaign,layout:{positions:compact}},catalog).mill,{x:1,y:6});
for (const point of [{x:0,y:0},{x:3,y:4},{x:0,y:6},{x:6,y:6},{x:1,y:5},{x:5,y:5},{x:8,y:6},{x:true,y:6}]) {
  assert.ok(validatePositions(campaign,catalog,{mill:point}));
}
assert.ok(validatePositions(campaign,catalog,{composter:{x:0,y:4}}));
assert.equal(validatePositions(campaign,catalog,{mill:{x:6,y:6},oven:{x:3,y:6}}),null);
const installed = {...campaign,recycling:{enabled:false}};
assert.deepEqual(Object.keys(compactPositions(installed,catalog)),catalog.layout.movable);
assert.equal(validatePositions(installed,catalog,catalog.layout.compact),null);
assert.deepEqual(routeCosts(installed,catalog).map(r=>r.moves),[3,3,4,6,4,10]);
assert.deepEqual(routeCosts(installed,catalog,catalog.layout.compact).map(r=>r.moves),[1,1,8,4,1,5]);
assert.equal(JSON.stringify(catalog),original);
console.log('Layout previews, reserved pads, named destinations and route distances passed.');
