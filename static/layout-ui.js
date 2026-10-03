import {layoutEntities, withPositions, validatePositions, routeCosts, compactPositions} from './layout-rules.js';

const $ = id => document.getElementById(id);
let state, catalog, busy = true, draft = {}, signature = null, viewKey = null, apply, preview;

const positions = () => state.layout?.positions || {};
function changed() {
  const current = layoutEntities(state,catalog), proposed = layoutEntities(state,catalog,draft);
  return Object.keys(current).some(name => current[name].x !== proposed[name].x || current[name].y !== proposed[name].y);
}

function draw() {
  const available = state?.scenario === 'factory' && !state.challenge;
  $('layout-panel').hidden = !available;
  if (!available) { preview(null); return; }
  const current = layoutEntities(state,catalog), proposed = layoutEntities(state,catalog,draft);
  const name = $('layout-machine').value;
  const problem = validatePositions(state,catalog,draft);
  const anyChange = changed();
  $('layout-mode').textContent = state.layout ? 'Custom layout' : 'Default layout';
  $('layout-machine').disabled = busy;
  $('layout-compact').disabled = $('layout-default').disabled = busy;
  $('layout-apply').disabled = busy || Boolean(problem) || !anyChange || state.order.status === 'active';
  $('layout-revert').disabled = busy || !anyChange;
  $('layout-target').textContent = `${current[name].title}: (${current[name].x}, ${current[name].y}) → (${proposed[name].x}, ${proposed[name].y})`;
  $('layout-note').textContent = busy ? 'Stop your program before editing a layout.' : state.order.status === 'active' ? 'Plan now; finish the active delivery order before applying a layout.' : problem || (anyChange ? 'Preview only. Apply to move machines with all stock and batches.' : 'Choose a machine, then a lane pad. Moves are free and take no farm ticks.');
  const definitions = withPositions({...catalog.entities,...catalog.recycling.entities},draft);
  $('layout-grid').innerHTML = Array.from({length:64},(_,index) => {
    const x=index%8,y=Math.floor(index/8);
    const occupant = Object.entries(definitions).find(([,d])=>d.x===x && d.y===y)?.[0];
    const reason = validatePositions(state,catalog,{...draft,[name]:{x,y}});
    const cropped = x < catalog.field.width && y < catalog.field.height;
    const rock = catalog.obstacles.some(([ox,oy])=>ox===x && oy===y);
    const marker = cropped ? '·' : rock ? '◆' : occupant ? ({mill:'M',oven:'O',chest:'S',depot:'D',composter:'C',mixer:'F'}[occupant] || 'W') : `${x},${y}`;
    const active = proposed[name].x===x && proposed[name].y===y;
    return `<button type="button" data-pad="${index}" class="layout-pad ${cropped || rock ? 'terrain' : ''} ${occupant ? 'occupied' : ''} ${active ? 'selected' : ''}" aria-label="Pad ${x}, ${y}${occupant ? ' · '+occupant : ''}${reason ? ' · '+reason : ''}" aria-pressed="${active}" title="${reason || `Place ${name} at (${x}, ${y})`}" ${busy || reason ? 'disabled' : ''}>${marker}</button>`;
  }).join('');
  const before = routeCosts(state,catalog), after = routeCosts(state,catalog,draft);
  $('layout-routes').innerHTML = before.map((route,i) => `<div><span>${route.from} → ${route.to}</span><strong>${route.moves}${route.moves !== after[i].moves ? ` → ${after[i].moves}` : ''} ${after[i].moves === 1 ? 'move' : 'moves'}</strong></div>`).join('');
  preview(!busy && $('layout-panel').open ? {machine:name,...proposed[name],valid:!problem} : null);
}

export function setupLayout(rules, onApply, onPreview) {
  catalog = rules; apply = onApply; preview = onPreview;
  $('layout-grid').addEventListener('click', event => {
    const pad = event.target.closest('[data-pad]');
    if (!pad || pad.disabled || busy) return;
    const index = Number(pad.dataset.pad), name = $('layout-machine').value;
    draft = {...draft,[name]:{x:index%8,y:Math.floor(index/8)}}; draw();
    $('layout-grid').querySelector(`[data-pad="${index}"]`).focus({preventScroll:true});
  });
  $('layout-machine').addEventListener('change',draw);
  $('layout-panel').addEventListener('toggle',()=>{if (state) draw();});
  $('layout-compact').addEventListener('click',()=>{draft=compactPositions(state,catalog); draw();});
  $('layout-default').addEventListener('click',()=>{draft={}; draw();});
  $('layout-revert').addEventListener('click',()=>{draft=structuredClone(positions()); draw();});
  $('layout-apply').addEventListener('click',()=>{if (!busy && !validatePositions(state,catalog,draft) && changed()) apply(structuredClone(draft));});
}

export function updateLayout(next, rules, isBusy) {
  state=next; catalog=rules || catalog; busy=isBusy;
  const nextSignature = state.scenario === 'factory' && !state.challenge ? JSON.stringify([state.layout || null,Boolean(state.recycling)]) : null;
  const nextKey = JSON.stringify([nextSignature,busy,state.order?.status]);
  if (nextKey === viewKey) return;
  viewKey = nextKey;
  if (nextSignature !== signature) {
    signature=nextSignature; draft=structuredClone(positions());
    if (nextSignature) {
      const names = catalog.layout.movable.filter(name=>!['composter','mixer'].includes(name) || state.recycling);
      const selected=$('layout-machine').value;
      $('layout-machine').innerHTML=names.map(name=>`<option value="${name}">${layoutEntities(state,catalog)[name].title}</option>`).join('');
      $('layout-machine').value=names.includes(selected) ? selected : 'mill';
    }
  }
  draw();
}

export function layoutGuide() {
  return `<p><strong>Make your routes part of the design.</strong> Stop your Breadworks campaign program, open Workshop layout, choose a machine and a numbered lane pad. The map outlines the draft pad and the route table previews shortest movement distances. Apply layout commits your plan. Compact workshop and Default layout are editable previews; Discard preview restores your saved positions.</p><p>The mill, oven and installed composter/mixer can move. Chest, depot and well stay fixed; crops, rocks and other machines cannot share a pad. Uninstalled recycling pads stay reserved so turning that module on never overlaps a building. Machines are passable docking pads; drones fly over them.</p><p>Moving is free and takes no ticks. Stock, active batches, growing options, drones and coins are kept. Finish an active delivery order before applying changes. Challenges keep their fixed maps. Programs using <code>navigate_to("mill")</code> and the other named destinations follow the new positions automatically; hardcoded coordinates must be updated by you.</p><h3>Measure the result</h3><p>Export a save before experimenting. Run <strong>Layout delivery test</strong> with at least 8 chest wheat, 8 cargo slots and empty bakery machines. It carries flour one item at a time, so machine spacing matters. Compare the same starting stock and code between layouts; shorter trips also give machines fewer ticks to process, so distance alone does not prove better throughput. Restart measurement to compare a new campaign window. Continuous and team examples also use named routes.</p><p>Layouts save with the campaign and portable checkpoints restore paused. Stop before moving to discard an old controller route. This milestone relocates existing machines; extra machines, conveyors, power and standalone blueprint sharing are future scope.</p>`;
}
