const $ = id => document.getElementById(id);

export function setupCare(rules, onChange) {
  $('care-settings').innerHTML = Object.entries(rules.features).map(([key, feature]) => `<label class="care-option"><span><input type="checkbox" id="care-${key}" data-feature="${key}"><strong>${feature.title}</strong></span><small>${feature.description}</small></label>`).join('');
  document.querySelectorAll('[data-feature]').forEach(input => input.addEventListener('change', () => {
    const settings = Object.fromEntries([...document.querySelectorAll('[data-feature]')].map(field => [field.dataset.feature, field.checked]));
    onChange(settings);
  }));
}

export function updateCare(state, rules, busy) {
  const care = state.care;
  for (const key of Object.keys(rules.features)) {
    $(`care-${key}`).checked = care.settings[key]; $(`care-${key}`).disabled = busy;
  }
  const enabled = Object.keys(care.settings).filter(key => care.settings[key]);
  $('care-mode').textContent = enabled.length ? `${enabled.length} system${enabled.length === 1 ? '' : 's'} on` : 'Simple farming';
  $('care-supplies').textContent = `Fertilizer ${care.fertilizer} · Compost ${care.compost} · Water ${care.tank}/${rules.tank_capacity}`;
  $('care-network').textContent = `${care.sprinklers.length} sprinklers · ${!care.settings.irrigation ? 'irrigation off' : !care.pump ? 'pump paused' : care.tank === 0 ? 'tank empty — refill at (0, 0)' : 'pump ready'} · supply well at (0, 0)`;
  $('care-goals').innerHTML = rules.goals.map(goal => `<div><strong>${care.completed.includes(goal.id) ? '✓ ' : ''}${goal.title}</strong><span>${Math.min(care.stats[goal.stat],goal.target)}/${goal.target} · +${goal.reward} coins</span><progress max="${goal.target}" value="${Math.min(care.stats[goal.stat],goal.target)}" aria-label="${goal.title} progress"></progress></div>`).join('');
}

export function describeCare(state, index) {
  const care = state.care, plot = care.plots[index], parts = [];
  if (care.settings.soil) parts.push(`soil ${plot.nutrients}%${plot.nutrients < 30 ? ' · slow growth' : ''}`);
  if (care.settings.fertilizer && plot.fertilized) parts.push(`fertilized${plot.boost ? ` · ${plot.boost} boost ticks` : ''}`);
  if (care.sprinklers.includes(index)) parts.push(care.settings.irrigation ? 'sprinkler installed' : 'sprinkler off');
  return parts.length ? ` · ${parts.join(' · ')}` : '';
}

export function cultivationGuide() {
  return `<p><strong>Choose how deeply you want to farm.</strong> Enable any combination in Growing options. Defaults keep the original farming rules. Settings, supplies, equipment, and progress belong to each chapter.</p><h3>Fertilizer</h3><p>Start with 6 doses. Feed a growing crop once to double its growth for 6 action ticks and restore 10 nutrients. Fertilized crops sell for 50% more (rounded down bonus) in Home farm, or yield 4 wheat instead of 3 in Breadworks. Buy more at the supply well (0, 0) for 2 coins per dose.</p><h3>Irrigation</h3><p>Install a sprinkler on any growing plot for 8 coins; it coexists with crops. It covers this plot and its eight neighbors. Every sixth world tick, each sprinkler spends 1 tank water if its area needs moisture, setting those plots to 12 moisture. Up to 9 sprinklers share a 60-unit tank. Manual water() spends 2 tank water with this option on. Refill for free at (0, 0). Sprinklers work during all drone actions, including factory deliveries.</p><h3>Soil health</h3><p>Soil starts at 100 nutrients. Harvesting uses 20 for wheat, 30 for carrots, or 15 for sunflowers, and gives 1 compost. Below 30 nutrients, watered crops grow only on even-numbered world ticks. Apply compost to restore 40 nutrients. Fertilizer can also restore some nutrients if enabled. Crops never die; turn off soil health to suspend the slowdown.</p><h3>Automation API</h3><table><thead><tr><th>Call</th><th>What it does</th></tr></thead><tbody><tr><td><code>fertilize()</code></td><td>Use one dose on a growing crop. Requires Fertilizer on.</td></tr><tr><td><code>buy_fertilizer(4)</code></td><td>Buy doses at (0, 0), 2 coins each; max 100 stored.</td></tr><tr><td><code>compost()</code></td><td>Use one compost on soil below 100 nutrients. Requires Soil health on.</td></tr><tr><td><code>install_sprinkler()</code></td><td>Install on this growing plot. Requires Irrigation on.</td></tr><tr><td><code>refill_tank()</code></td><td>Refill at (0, 0). The current action may then trigger a sprinkler pulse.</td></tr><tr><td><code>set_irrigation(True)</code></td><td>Turn the pump on or off with True / False; does not disable the irrigation rules.</td></tr><tr><td><code>feature_enabled("soil")</code></td><td>Read an option: fertilizer, irrigation, or soil.</td></tr><tr><td><code>get_nutrients()</code></td><td>Current plot's nutrients, 0–100.</td></tr><tr><td><code>get_supply("water")</code></td><td>Amount of water, fertilizer, or compost available.</td></tr><tr><td><code>has_sprinkler()</code>, <code>is_fertilized()</code></td><td>Check this plot's equipment / current crop treatment.</td></tr><tr><td><code>get_yield()</code></td><td>Factory wheat per harvest (3 or 4); Home farm returns one crop.</td></tr><tr><td><code>get_scenario()</code></td><td>Returns classic or factory.</td></tr></tbody></table><p>All six actions cost one tick. Queries cost no ticks and still consume interpreter budget. Failed actions do not use resources or time.</p><h3>Try it</h3><p>Enable your preferred systems, then load <strong>Smart crop care</strong>. It tends six plots, checks nutrients, feeds crops, restocks at the well, and handles factory cargo. Rerun it for another harvest. <strong>Sprinkler network</strong> lays out 3×3 coverage as funds allow and runs a refill controller. Its sprinklers continue watering during your other programs.</p><p>Optional growing goals reward 6 fertilizer applications (+20), 36 plot waterings by sprinklers (+25), and 6 compost applications (+30). These goals are independent of chapter missions.</p><p>Switching a system off suspends its growth/resource rules and retains equipment, supplies, and soil. Manual watering becomes free when irrigation is off. Untouched fertilizer boosts pause while disabled; harvesting still clears that crop's treatment. Existing simple examples can need resource checks with these options on; Smart crop care demonstrates them.</p>`;
}
