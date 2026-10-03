import {withPositions, layoutEntities} from './layout-rules.js';
const $ = id => document.getElementById(id);

export function factoryEntities(state, catalog) {
  return layoutEntities(state,catalog);
}

function label(state, rules, name) {
  const line = state.recycling, machine = line.machines[name], rule = rules.entities[name];
  if (!line.enabled) return `Paused${machine.remaining ? ` · batch has ${machine.remaining} ticks left` : ' · stock kept'}`;
  if (machine.remaining) return `Working · ${machine.remaining} ticks left`;
  if (machine.output + rule.output_amount > rule.output_capacity) return 'Output blocked · collect products';
  return machine.input >= rule.amount ? 'Ready · take an action to start' : `Waiting for ${rule.ingredient}`;
}

export function describeRecyclingTile(state, rules, x, y) {
  if (!state.recycling) return null;
  const match = Object.entries(withPositions(rules.entities,state.layout?.positions)).find(([, d]) => d.x === x && d.y === y);
  if (!match) return null;
  const [name, rule] = match;
  return name === 'well' ? `${rule.title} · ${state.recycling.residue}/${rules.hopper_capacity} residue` : `${rule.title} · ${label(state, rules, name)}`;
}

export function setupRecycling(rules, onChange) {
  $('recycling-toggle').addEventListener('change', event => onChange(event.target.checked));
  $('recycling-cards').innerHTML = Object.entries(rules.entities).map(([name, d]) => `<article class="production-card ${name}"><div class="production-title"><strong>${d.title}</strong><span id="recycling-position-${name}">(${d.x}, ${d.y})</span></div><p>${name === 'well' ? 'Harvest residue → drone transport' : `${d.amount} ${d.ingredient} → ${d.output_amount} ${d.product} · ${d.ticks} ticks`}</p><strong id="recycling-stock-${name}" class="production-stock"></strong>${name !== 'well' ? `<progress id="recycling-process-${name}" max="${d.ticks}" value="0" aria-label="${d.title} batch progress"></progress>` : ''}<span id="recycling-status-${name}" class="production-status"></span></article>`).join('');
}

export function updateRecycling(state, rules, busy) {
  const available = state.scenario === 'factory' && !state.challenge;
  $('recycling-panel').hidden = !available;
  if (!available) return;
  const line = state.recycling;
  $('recycling-toggle').checked = Boolean(line?.enabled);
  $('recycling-toggle').disabled = busy;
  $('recycling-mode').textContent = line?.enabled ? 'Production on' : line ? 'Paused · stock kept' : 'Optional';
  $('recycling-dashboard').hidden = !line;
  if (!line) return;
  for (const [name,d] of Object.entries(withPositions(rules.entities,state.layout?.positions))) $('recycling-position-'+name).textContent = `(${d.x}, ${d.y})`;
  $('recycling-stock-well').textContent = `${line.residue}/${rules.hopper_capacity} residue · ${state.care.compost} compost · ${state.care.fertilizer} fertilizer`;
  $('recycling-status-well').textContent = line.enabled && line.residue === rules.hopper_capacity ? 'Hopper full · transport residue before harvesting' : 'Return finished supplies here to use them on crops';
  for (const name of ['composter', 'mixer']) {
    const m = line.machines[name], d = rules.entities[name];
    $('recycling-stock-' + name).textContent = `${m.input}/${d.input_capacity} in · ${m.output}/${d.output_capacity} out`;
    $('recycling-status-' + name).textContent = label(state, rules, name);
    $('recycling-process-' + name).value = m.remaining ? d.ticks - m.remaining : 0;
  }
  $('recycling-totals').textContent = `Collected ${line.stats.residue_collected} residue · made ${line.stats.compost_produced} compost & ${line.stats.fertilizer_produced} fertilizer`;
  $('recycling-goals').innerHTML = [['compost', 4], ['fertilizer', 8]].map(([item, target]) => {
    const n = line.stats[item + '_returned'];
    return `<div><strong>${n >= target ? '✓ ' : ''}Return ${target} ${item}</strong><span>${Math.min(n,target)}/${target} delivered to the well</span><progress max="${target}" value="${Math.min(n,target)}" aria-label="Returned ${item}"></progress></div>`;
  }).join('');
}

export function recyclingGuide(rules) {
  return `<p><strong>Make your farm supply itself.</strong> In the Breadworks campaign, open Crop recycling and enable its switch. Each harvest puts one residue in the supply well's ${rules.hopper_capacity}-item hopper. It does not take cargo space. A full hopper blocks harvesting until you transport residue. Growing options remain independent.</p><ol><li>Load residue at <code>navigate_to("well")</code>, then unload it at <code>navigate_to("composter")</code>.</li><li>Collect compost from the composter. Return some to the well for soil care, or carry it to the mixer for fertilizer.</li><li>Collect fertilizer from the mixer and unload it at the well. Enable Fertilizer or Soil health to use these shared supplies on crops.</li></ol><table><thead><tr><th>Building</th><th>Recipe</th><th>Time</th><th>Buffers</th></tr></thead><tbody>${['composter','mixer'].map(name => {const d=rules.entities[name]; return `<tr><td>${d.title} (${d.x}, ${d.y})</td><td>${d.amount} ${d.ingredient} → ${d.output_amount} ${d.product}</td><td>${d.ticks} ticks</td><td>${d.input_capacity} in / ${d.output_capacity} out</td></tr>`;}).join('')}</tbody></table><p>Use existing <code>load()</code>, <code>unload()</code>, <code>stored()</code>, <code>free_space()</code>, <code>cargo()</code> and <code>machine_status()</code> calls with the new buildings and items. <code>feature_enabled("recycling")</code> checks the switch. Cargo and chest capacity are shared across all six items. Machines reserve room for two output items before starting; transport keeps them moving. Both drones share the same production tick.</p><h3>A choice at the composter</h3><p>One compost restores 40 soil nutrients. Sending it to the mixer instead makes two fertilizer doses, each restoring 10 nutrients and improving a growing crop's yield. Keep some compost for poor soil and divert the surplus. With recycling on, Soil health harvests give residue instead of instant compost. Home farm keeps its original behavior.</p><h3>Try the examples</h3><p><strong>First recycled fertilizer</strong> harvests two plots and returns one compost and two fertilizer. <strong>Recycling autopilot</strong> runs continuously, feeds the bakery, reserves compost for soil care and produces fertilizer when that option is on. It uses your current supplies and does not buy fertilizer. The two return goals track progress without coin rewards.</p><p>Stop before changing options. Switching recycling off pauses its machines and keeps materials and active batches; transfers still work. Soil health then returns to instant compost at harvest. Re-enable to resume. The well accepts returned compost up to 1,000 and fertilizer up to 100; these are available to both drones. Existing purchased supplies cannot be loaded out of the well. With both care options off, compost accumulates: enable a use for it, store it, or pause recycling before supplies fill. Challenge farms keep their fixed rules.</p>`;
}
