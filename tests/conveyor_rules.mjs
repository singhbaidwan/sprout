import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const load=async file=>import(`data:text/javascript;base64,${Buffer.from(readFileSync(new URL(file,import.meta.url),'utf8')).toString('base64')}`);
const {autoPath,pathProblem,padAllowed,endpoints,conveyorStatus,describeConveyorPad}=await load('../static/conveyor-rules.js');
const {validatePositions}=await load('../static/layout-rules.js');
const catalog={entities:{chest:{x:0,y:6},mill:{x:3,y:6},oven:{x:6,y:6},depot:{x:7,y:3}},
  recycling:{entities:{well:{x:0,y:0},composter:{x:1,y:5},mixer:{x:5,y:5}}},
  field:{width:6,height:4},obstacles:[[6,2],[6,3],[3,4]],layout:{movable:['mill','oven','composter','mixer']},
  conveyors:{max_path:32,routes:{grain:{source:'chest',target:'mill'},flour:{source:'mill',target:'oven'},bread:{source:'oven',target:'depot'}}}};
const state={scenario:'factory',machines:{mill:{input:0},oven:{input:0}}};
const original=JSON.stringify(catalog);
assert.deepEqual(autoPath(state,catalog,'grain'),[48,49,50,51]);
assert.deepEqual(autoPath(state,catalog,'flour'),[51,52,53,54]);
assert.deepEqual(autoPath(state,catalog,'bread'),[54,55,47,39,31]);
for(const name of ['grain','flour','bread'])assert.equal(pathProblem(state,catalog,name,autoPath(state,catalog,name)),null);
for(const path of [[48],[48,51],[48,49,48,49,50,51],[48,40,41,42,43,51],[48,true,50,51]])assert.ok(pathProblem(state,catalog,'grain',path));
assert.equal(padAllowed(state,catalog,'grain',41),false); // Reserved composter.
const compact={...state,layout:{positions:{mill:{x:1,y:6},oven:{x:2,y:6}}}};
assert.deepEqual(endpoints(compact,catalog,'grain'),[48,49]);
assert.deepEqual(autoPath(compact,catalog,'flour'),[49,50]);
const built={...state,conveyors:{enabled:true,routes:{grain:{path:[48,49,50,51],feeding:true,slots:[1,0,0]}}}};
assert.equal(conveyorStatus(built,'grain'),'Moving');
assert.equal(describeConveyorPad(built,catalog,1,6),'grain conveyor · empty segment');
assert.equal(conveyorStatus({...built,chest:{wheat:12},conveyors:{enabled:true,routes:{grain:{feeding:true,slots:[0,0,0]}}}},'grain'),'Ready · feed on');
assert.equal(conveyorStatus({...built,conveyors:{...built.conveyors,enabled:false}},'grain'),'Paused · queue kept');
assert.equal(conveyorStatus({...built,machines:{mill:{input:12}},conveyors:{enabled:true,routes:{grain:{feeding:true,slots:[1,1,1]}}}},'grain'),'Blocked · input full');
assert.ok(validatePositions(built,catalog,{mill:{x:1,y:6}}));
assert.equal(validatePositions(built,catalog,{}),null);
assert.equal(JSON.stringify(catalog),original);
console.log('Conveyor paths, reserved pads, custom layouts, queues and relocation guards passed.');
