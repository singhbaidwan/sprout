import {endpoints,padAllowed,pathProblem,autoPath,conveyorStatus} from './conveyor-rules.js';
const $=id=>document.getElementById(id);
let state,catalog,busy=true,draft={},signature=null,apply,preview;
const plan=()=>Object.fromEntries(Object.entries(state.conveyors?.routes||{}).map(([name,r])=>[name,{path:[...r.path],feeding:r.feeding}]));
const changed=()=>JSON.stringify(draft)!==JSON.stringify(plan());
const selected=()=>$('conveyor-route').value;
function problems() {
  for(const [name,r] of Object.entries(draft)) {const error=pathProblem(state,catalog,name,r.path);if(error)return error;}
  for(const [name,r] of Object.entries(state.conveyors?.routes||{})) if(r.slots.some(Boolean) && (!draft[name] || JSON.stringify(draft[name].path)!==JSON.stringify(r.path))) return 'Stop feeding and run until this queue drains before changing its path.';
  return null;
}
function draw() {
  const available=state?.scenario==='factory' && !state.challenge;
  $('conveyor-panel').hidden=!available;
  if(!available){preview(null);return;}
  const locked=busy || state.order.status==='active',name=selected(),rule=catalog.conveyors.routes[name],current=state.conveyors?.routes[name];
  const path=draft[name]?.path || [endpoints(state,catalog,name)[0]],end=endpoints(state,catalog,name)[1];
  const issue=problems();
  $('conveyor-mode').textContent=state.conveyors?.enabled ? 'Belts on' : state.conveyors ? 'Paused' : 'Optional';
  $('conveyor-enabled').checked=Boolean(state.conveyors?.enabled);
  $('conveyor-enabled').disabled=locked || !Object.keys(state.conveyors?.routes||{}).length;
  for(const id of ['conveyor-route','conveyor-auto','conveyor-preset','conveyor-clear','conveyor-revert']) $(id).disabled=locked;
  $('conveyor-remove').disabled=locked || !draft[name] || Boolean(current?.slots.some(Boolean));
  $('conveyor-drain').disabled=locked || !Object.values(state.conveyors?.routes||{}).some(r=>r.feeding);
  $('conveyor-apply').disabled=locked || !changed() || Boolean(issue);
  $('conveyor-target').textContent=`${rule.source} → ${rule.target} · ${rule.item} · ${path.length-1} ${path.length===2?'segment':'segments'}${path.at(-1)===end ? ' · connected' : ' · draw to destination'}`;
  $('conveyor-note').textContent=busy ? 'Stop your program before building or configuring belts.' : state.order.status==='active' ? 'Finish the active order before rebuilding. Python feed switches can still run.' : issue || (changed() ? 'Preview only. Apply routes keeps stock on unchanged paths and enables transport.' : 'Choose a route, then draw adjacent pads or use Auto-route. Crossings have independent tracks.');
  $('conveyor-grid').innerHTML=Array.from({length:64},(_,cell)=>{
    const index=path.indexOf(cell),last=path.at(-1),adjacent=Math.abs(last%8-cell%8)+Math.abs(Math.floor(last/8)-Math.floor(cell/8))===1;
    const allowed=padAllowed(state,catalog,name,cell) && (index>=0 || path.at(-1)!==end && adjacent && path.length<catalog.conveyors.max_path);
    const title=index===0?'Source':cell===end?'Destination':index>=0?`Step ${index}`:`Pad ${cell%8}, ${Math.floor(cell/8)}`;
    return `<button type="button" data-belt-pad="${cell}" class="layout-pad ${index>=0?'selected':''}" aria-label="${title} at ${cell%8}, ${Math.floor(cell/8)}${!allowed?' · choose an adjacent lane pad':''}" title="${title}" ${locked || !allowed?'disabled':''}>${index===0?'S':cell===end?'D':index>=0?index:padAllowed(state,catalog,name,cell)?`${cell%8},${Math.floor(cell/8)}`:'·'}</button>`;
  }).join('');
  $('conveyor-cards').innerHTML=Object.entries(catalog.conveyors.routes).map(([key,d])=>{
    const r=state.conveyors?.routes[key],count=r?r.slots.reduce((a,b)=>a+b,0):0;
    return `<article class="conveyor-card"><strong>${d.title}</strong><span>${d.source} → ${d.target}</span><p>${conveyorStatus(state,key)}</p><b>${r?`${count}/${r.slots.length} queued · ${r.delivered} arrived`:'Build a route to start'}</b><label><input type="checkbox" data-conveyor-feed="${key}" aria-label="${d.title} feed" ${r?.feeding?'checked':''} ${locked || !r?'disabled':''}> Feed new ${d.item}</label></article>`;
  }).join('');
  preview(!busy && $('conveyor-panel').open ? {name,path} : null);
}
export function setupConveyors(rules,onApply,onPreview) {
  catalog=rules;apply=onApply;preview=onPreview;
  $('conveyor-grid').addEventListener('click',event=>{
    const b=event.target.closest('[data-belt-pad]');if(!b || b.disabled)return;
    const name=selected(),cell=Number(b.dataset.beltPad),path=draft[name]?.path||[endpoints(state,catalog,name)[0]],index=path.indexOf(cell);
    draft[name]={path:index>=0?path.slice(0,index+1):[...path,cell],feeding:draft[name]?.feeding??true};draw();
    $('conveyor-grid').querySelector(`[data-belt-pad="${cell}"]`).focus({preventScroll:true});
  });
  $('conveyor-route').addEventListener('change',draw);
  $('conveyor-panel').addEventListener('toggle',()=>{if(state)draw();});
  $('conveyor-auto').addEventListener('click',()=>{const name=selected(),path=autoPath(state,catalog,name);if(path)draft[name]={path,feeding:draft[name]?.feeding??true};else $('conveyor-note').textContent='No lane route fits. Try moving a machine after removing its empty belts.';if(path)draw();});
  $('conveyor-preset').addEventListener('click',()=>{
    const proposed={};for(const name of Object.keys(catalog.conveyors.routes)){const path=autoPath(state,catalog,name);if(!path){$('conveyor-note').textContent='This layout needs a manual route or different machine placement.';return;}proposed[name]={path,feeding:draft[name]?.feeding??true};}draft=proposed;draw();
  });
  $('conveyor-clear').addEventListener('click',()=>{const name=selected();draft[name]={path:[endpoints(state,catalog,name)[0]],feeding:true};draw();});
  $('conveyor-remove').addEventListener('click',()=>{delete draft[selected()];draw();});
  $('conveyor-revert').addEventListener('click',()=>{draft=plan();draw();});
  $('conveyor-apply').addEventListener('click',()=>{if(!busy && !problems() && changed())apply(true,structuredClone(draft));});
  $('conveyor-enabled').addEventListener('change',event=>apply(event.target.checked,plan()));
  $('conveyor-cards').addEventListener('change',event=>{const key=event.target.dataset.conveyorFeed;if(!key)return;const routes=plan();routes[key].feeding=event.target.checked;apply(Boolean(state.conveyors?.enabled),routes);});
  $('conveyor-drain').addEventListener('click',()=>{const routes=plan();for(const r of Object.values(routes))r.feeding=false;apply(true,routes);});
}
export function updateConveyors(next,rules,isBusy) {
  state=next;catalog=rules||catalog;busy=isBusy;
  const sig=JSON.stringify([state.layout||null,Object.entries(state.conveyors?.routes||{}).map(([name,r])=>[name,r.path,r.feeding])]);
  if(sig!==signature){signature=sig;draft=state.scenario==='factory'?plan():{};}
  draw();
}
export function conveyorGuide() {
  return `<p><strong>Let infrastructure carry bread while your Python tends the farm.</strong> Stop in Breadworks, open Conveyor workshop, choose a line and draw adjacent lane pads from S to D. Click an earlier pad to backtrack. Auto-route suggests a shortest lane path; Auto-connect bakery previews all three routes. Apply routes builds them and enables transport. Moves cost no coins or ticks.</p><p>Each segment holds one item. Belts pick up at most one item per world tick and items travel at most one segment per tick. Newly made machine products enter next tick. A full destination backs the queue up; no items disappear. Crossings are independent tracks, and drones fly over belts. Only grain chest → mill, flour mill → oven and bread oven → depot are supported. Bread arrives as a sale and counts toward missions and delivery orders.</p><p><strong>Feed off drains; pause freezes.</strong> Stop feeds and drain switches every inlet off and enables transport. Run actions or waits until Queued reaches zero before rerouting/removing. Enable conveyors off pauses every queue. Remove connected empty routes before moving machines. Finish active orders before workshop configuration; Python feed gates remain available. Fixed challenges do not permit conveyors.</p><h3>Program the policy</h3><pre>set_conveyor_feed("grain", stored("chest", "wheat") > 4)\nprint(conveyor_status("flour"), conveyor_items("flour"))</pre><p><code>set_conveyor_feed(name, True/False)</code> is a remote one-tick action; it needs a built route. <code>conveyor_items(name)</code> returns queued items, zero if not built. <code>conveyor_status(name)</code> returns not_installed, paused, blocked, moving, drained, ready or waiting_input. Names are grain, flour, bread. Both drones share gates; simultaneous changes to the same gate alternate priority.</p><p><strong>Conveyor delivery</strong> is a finite four-loaf demo. <strong>Conveyor farmer</strong> selects Continuous, supplies wheat, gates its feed and handles optional crop care/recycling. Original manual-transfer tutorials assume their stock stays available: pause conveyors before running those. Factory stock queries exclude belt items; inspect conveyor queues separately. Saves keep exact paths, queues and gate states; reload restores controllers paused. There is no wall-clock/offline growth.</p>`;
}
