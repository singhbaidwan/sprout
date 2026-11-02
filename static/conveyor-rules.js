// Pure bounded path planning; Python remains the authority for configuration.
export function stations(state, catalog) {
  return Object.fromEntries(Object.entries({...catalog.entities,...catalog.recycling.entities}).map(([name,d])=>[name,{...d,...state.layout?.positions[name]}]));
}
const cellOf = d => d.y*8+d.x;
export function endpoints(state,catalog,name) {
  const places=stations(state,catalog),rule=catalog.conveyors.routes[name];
  return [cellOf(places[rule.source]),cellOf(places[rule.target])];
}
export function padAllowed(state,catalog,name,cell) {
  const x=cell%8,y=Math.floor(cell/8),ends=endpoints(state,catalog,name);
  return Number.isInteger(cell) && cell>=0 && cell<64 && !(x<catalog.field.width && y<catalog.field.height) && !catalog.obstacles.some(([ox,oy])=>x===ox && y===oy) && (ends.includes(cell) || !Object.values(stations(state,catalog)).some(d=>cellOf(d)===cell));
}
export function pathProblem(state,catalog,name,path) {
  if (!catalog.conveyors.routes[name] || !Array.isArray(path) || path.length<2 || path.length>catalog.conveyors.max_path) return 'Draw a connected route of 2–32 pads.';
  const [start,end]=endpoints(state,catalog,name);
  if(path[0]!==start || path.at(-1)!==end) return 'Finish at the destination building.';
  if(new Set(path).size!==path.length) return 'A route cannot repeat a pad.';
  for(let i=0;i<path.length;i++) {
    if(!padAllowed(state,catalog,name,path[i]) || i>0 && i<path.length-1 && [start,end].includes(path[i])) return 'Avoid crops, rocks and unrelated buildings.';
    if(i && Math.abs(path[i]%8-path[i-1]%8)+Math.abs(Math.floor(path[i]/8)-Math.floor(path[i-1]/8))!==1) return 'Pads must touch along an edge.';
  }
  return null;
}
export function autoPath(state,catalog,name) {
  const [start,end]=endpoints(state,catalog,name),queue=[[start]],seen=new Set([start]);
  for(let i=0;i<queue.length;i++) {
    const path=queue[i],last=path.at(-1);
    if(last===end) return path;
    if(path.length>=catalog.conveyors.max_path) continue;
    for(const [dx,dy] of [[1,0],[0,1],[-1,0],[0,-1]]) {
      const x=last%8+dx,y=Math.floor(last/8)+dy,cell=y*8+x;
      if(x>=0 && x<8 && y>=0 && y<8 && !seen.has(cell) && padAllowed(state,catalog,name,cell)) {seen.add(cell);queue.push([...path,cell]);}
    }
  }
  return null;
}
export function conveyorStatus(state,name) {
  const route=state.conveyors?.routes[name];
  if(!route) return 'Not built';
  if(!state.conveyors.enabled) return 'Paused · queue kept';
  if(name==='bread_store' && route.slots.at(-1) && Object.values(state.chest).reduce((a,b)=>a+b,0)>=48)return 'Blocked · chest full';
  const target={grain:'mill',flour:'oven'}[name];
  if(route.slots.at(-1) && target && state.machines[target].input>=12) return 'Blocked · input full';
  if(route.slots.some(Boolean)) return 'Moving';
  if(!route.feeding) return 'Drained · feed off';
  return {ready:'Ready · feed on',routing_hold:'Holding · other bread branch selected',target_met:'Holding · target met',reserve_held:'Holding · reserve kept',waiting_input:`Waiting for ${name==='grain'?'wheat':name==='bread_store'?'bread':name}`}[intakeStatus(state,name)];
}

export function committedStock(state,name) {
  if(name==='bread')return null;
  const route=state.conveyors?.routes[name];if(!route)return 0;
  if(name==='bread_store')return state.chest.bread+route.slots.reduce((a,b)=>a+b,0);
  const machine=state.machines[name==='grain'?'mill':'oven'];
  return machine.input+route.slots.reduce((a,b)=>a+b,0)+(machine.remaining?(name==='grain'?2:1):0);
}
export function intakeStatus(state,name) {
  const route=state.conveyors?.routes[name];if(!route)return 'not_installed';
  if(!state.conveyors.enabled)return 'paused';
  if(!route.feeding)return 'feed_off';
  const mode=state.conveyors.routing?.mode;
  if(mode && ['bread','bread_store'].includes(name) && (mode==='sell' && name==='bread_store' || mode==='store' && name==='bread'))return 'routing_hold';
  const policy=route.policy;
  if(policy && policy.target!==null && committedStock(state,name)>=policy.target)return 'target_met';
  const stock=name==='grain'?state.chest.wheat:state.machines[name==='flour'?'mill':'oven'].output;
  if(!stock)return 'waiting_input';
  return policy && stock<=policy.reserve?'reserve_held':'ready';
}
export function policyProblem(name,reserve,target) {
  if(!['grain','flour','bread','bread_store'].includes(name))return 'Choose a bakery conveyor.';
  if(!Number.isInteger(reserve) || reserve<0 || reserve>(name==='grain'?48:8))return `Reserve must be a whole number from 0 to ${name==='grain'?48:8}.`;
  if(name==='bread' && target!==null)return 'The depot sells directly; bread has no destination target.';
  if(target!==null && (!Number.isInteger(target) || target<0 || target>(name==='bread_store'?48:12)))return `Target must be blank or a whole number from 0 to ${name==='bread_store'?48:12}.`;
  return null;
}

export function describeConveyorPad(state,catalog,x,y) {
  return Object.entries(state.conveyors?.routes||{}).flatMap(([name,r])=>{
    const index=r.path.indexOf(y*8+x);if(index<0)return [];
    const stock=index===r.path.length-1?'arrival dock':r.slots[index]?`1 ${catalog.conveyors.routes[name].item}`:'empty segment';
    return [`${name} conveyor · ${stock}${!state.conveyors.enabled?' · paused':''}`];
  }).join(' · ');
}
