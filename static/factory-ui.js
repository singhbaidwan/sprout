// Breadworks presentation reads its rules and recipes from the Python catalog.
const $ = id => document.getElementById(id);
const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

export function describeFactoryTile(state, catalog, x, y) {
  if (catalog.obstacles.some(([ox, oy]) => ox === x && oy === y)) return 'Rock · blocks movement';
  const entity = Object.entries(catalog.entities).find(([, entity]) => entity.x === x && entity.y === y);
  if (entity) {
    const [name, def] = entity;
    return `${def.title} · ${name === 'depot' ? `${def.price} coins per bread` : name === 'chest' ? `${Object.values(state.chest).reduce((a,b) => a+b,0)} / ${def.capacity} items` : machineLabel(state, catalog, name)}`;
  }
  return x >= catalog.field.width || y >= catalog.field.height ? 'Factory lane · travel freely, no planting' : null;
}

function machineLabel(state, catalog, name) {
  const m = state.machines[name], def = catalog.entities[name];
  if (m.remaining) return `Working · ${m.remaining} ticks left`;
  if (m.output >= def.output_capacity) return 'Output full · collect products';
  return m.input >= def.amount ? 'Ready · take an action to start' : `Waiting for ${def.ingredient}`;
}

export function setupFactory(catalog) {
  $('production-cards').innerHTML = Object.entries(catalog.entities).map(([name, def]) => `<article class="production-card ${name}"><div class="production-title"><strong>${escape(def.title)}</strong><span>(${def.x}, ${def.y})</span></div><p>${name === 'chest' ? `Shared storage · ${def.capacity} items` : name === 'depot' ? `Bread → ${def.price} coins each` : `${def.amount} ${def.ingredient} → 1 ${def.product}`}</p><strong id="stock-${name}" class="production-stock"></strong>${name === 'mill' || name === 'oven' ? `<progress id="process-${name}" max="${def.ticks}" value="0" aria-label="${def.title} batch progress"></progress>` : ''}<span id="status-${name}" class="production-status"></span></article>`).join('');
}

export function updateFactory(state, catalog, busy) {
  const capacity = catalog.cargo_capacity * (state.upgrades.includes('cargo') ? 2 : 1);
  $('cargo-count').textContent = `${Object.values(state.cargo).reduce((a,b) => a+b,0)} / ${capacity}`;
  $('cargo-items').textContent = Object.entries(state.cargo).map(([item, n]) => `${n} ${item}`).join(' · ');
  for (const name of ['mill', 'oven']) {
    const m = state.machines[name], def = catalog.entities[name];
    $('stock-' + name).textContent = `${m.input}/${def.input_capacity} in · ${m.output}/${def.output_capacity} out`;
    $('status-' + name).textContent = machineLabel(state, catalog, name);
    const duration = def.ticks / (state.upgrades.includes(name) ? 2 : 1);
    $('process-' + name).max = Math.max(duration, m.remaining + 1);
    $('process-' + name).value = m.remaining ? $('process-' + name).max - m.remaining : 0;
  }
  $('stock-chest').textContent = Object.entries(state.chest).map(([item, n]) => `${n} ${item}`).join(' · ');
  $('status-chest').textContent = `${catalog.entities.chest.capacity - Object.values(state.chest).reduce((a,b) => a+b,0)} slots available`;
  $('stock-depot').textContent = `${state.stats.bread_delivered} loaves delivered`;
  $('status-depot').textContent = `${state.stats.earned} coins from sales`;
  const order = state.order, rules = catalog.order;
  const delivered = Math.min(rules.target, state.stats.bread_delivered - order.start_delivered);
  $('order-progress').max = rules.target;
  $('order-progress').value = order.status === 'idle' ? 0 : delivered;
  $('order-detail').textContent = order.status === 'active' ? `${delivered}/${rules.target} delivered · ${Math.max(0, rules.deadline - state.tick + order.start_tick)} ticks left` : order.status === 'complete' ? `Order complete! +${rules.reward} coins. Ready for another?` : order.status === 'failed' ? 'Time ran out. Keep your stock, improve your route, and retry.' : `Deliver ${rules.target} bread in ${rules.deadline} ticks · +${rules.reward} coins`;
  $('order-best').textContent = order.best ? `Best: ${order.best} ticks · ${order.completed} orders completed` : 'Stockpiles count. Only drone actions use time.';
  $('start-order').disabled = busy || order.status === 'active' || state.stats.bread_delivered < rules.unlock;
  $('start-order').textContent = order.status === 'active' ? 'Order active' : state.stats.bread_delivered < rules.unlock ? `Unlock: deliver ${rules.unlock} bread` : order.status === 'failed' ? 'Retry order' : 'Start order';
}

export function factoryGuide(tab, catalog, missions) {
  if (tab === 'learn') return `<p><strong>Welcome to the Breadworks.</strong> Your drone is the connection between a wheat field and a working bakery. Both chapters keep their own progress and program.</p><ol><li><strong>Run First bread.</strong> The chest starts with 12 wheat. Supply 8 to the mill, carry 4 flour to the oven, then deliver 4 bread for coins and three mission rewards.</li><li><strong>Grow your supply.</strong> Run Harvest &amp; store to tend 24 plots. Each harvest adds 3 wheat to cargo. A full drone must unload before harvesting again.</li><li><strong>Keep production moving.</strong> Farm to bakery harvests a row and runs a repeatable supply routine. Machines work during movement, farming, transfers, and wait(). Diagnose idle machines using the live production panel.</li><li><strong>Improve and compete.</strong> Buy larger cargo or faster machines. Stock 24 wheat, start a timed order, then try Order runner. Complete six missions and improve your personal delivery record.</li></ol><h3>Time is part of the puzzle</h3><p>Every successful action advances crops and both machines once. Navigation costs one action per tile. Transfers cost one action regardless of quantity. Queries and browser waiting cost no ticks. Put <code>wait()</code> inside waiting loops. Finite runs keep the 400-action limit; pause, step, stop, and saves work as in Home farm.</p><h3>Know your map</h3><p>Farm at x 0–5, y 0–3. Buildings have named pads; navigate directly onto one to load or unload. Rocks block movement, and edges do not wrap. <code>navigate_to()</code> finds a shortest route around rocks.</p>`;
  if (tab === 'crops') return `<h3>One crop, a whole production line</h3><p>Wheat costs 1 coin to plant (free at zero coins), grows in 6 watered ticks, and yields 3 wheat into cargo. Water supplies 24 ticks of moisture. The chest holds 48 items; cargo starts at 8 and upgrades to 16.</p><table><thead><tr><th>Machine</th><th>Recipe</th><th>Time</th><th>Buffers</th></tr></thead><tbody>${['mill','oven'].map(name => {const d=catalog.entities[name]; return `<tr><td>${d.title}</td><td>${d.amount} ${d.ingredient} → ${d.product}</td><td>${d.ticks} ticks; ${d.ticks/2} upgraded</td><td>${d.input_capacity} in / ${d.output_capacity} out</td></tr>`;}).join('')}</tbody></table><p>Machines consume ingredients when a batch starts. A full output stops new batches. Upgrades speed up the next batch; an existing batch keeps its remaining time.</p><h3>Six missions</h3><ol>${missions.map(m=>`<li><strong>${escape(m.title)}</strong><br>${escape(m.description)} +${m.reward} coins.</li>`).join('')}</ol><p>Timed orders unlock after 4 bread delivered: deliver 12 more within 180 action ticks for 40 coins. Previously stored bread counts when delivered after the order starts. The final allowed tick counts. Orders have no penalty beyond missing the bonus.</p>`;
  const api = [
    ['navigate_to("mill")', 'Travel to chest, mill, oven, or depot; also navigate_to(x, y). Each route step costs one tick.'],
    ['load("wheat", 4)', 'At a chest, load any item. At a machine, load only its finished product. Needs free cargo slots.'],
    ['unload("wheat", 4)', 'At a chest, store cargo. At a machine, supply its ingredient. At the depot, sell bread.'],
    ['cargo("wheat") / cargo_space()', 'Read carried quantity / total available cargo slots.'],
    ['stored("mill", "flour")', 'Read completed flour. With wheat, reads mill input; active batches are excluded.'],
    ['free_space("mill", "wheat")', 'Read available input slots for this item. Chest shares capacity across items. Unsupported machine ingredients return 0.'],
    ['machine_status("oven")', 'Returns working, waiting_input, output_full, or ready.'],
    ['get_tick() / get_delivered()', 'Read world ticks / lifetime delivered bread.'],
    ['harvest()', 'Take 3 wheat from a ripe growing plot. Requires 3 cargo slots.'],
    ['move("east")', 'Move one tile; edges and rocks block movement.'],
    ['till(), plant("wheat"), water(), wait()', 'Prepare soil, sow wheat, add moisture, or let one tick pass.'],
  ];
  return `<p>Use the same bounded Python language: variables, conditions, loops, functions, lists, positional calls, and print(). No imports, arbitrary attributes, packages, or file access. Maximum 400 actions and 20,000 interpreter operations per run.</p><table><thead><tr><th>Command / query</th><th>Meaning</th></tr></thead><tbody>${api.map(([command, text])=>`<tr><td><code>${escape(command)}</code></td><td>${text}</td></tr>`).join('')}</tbody></table><p>Existing queries still work: can_harvest(), get_crop(), get_water(), is_tilled(), get_x(), get_y(), get_size(), get_coins(). get_size() is the whole map width (8), not the growing-field width (6).</p><p>Transfers require a positive integer amount and happen entirely or fail without changes. The drone must be on the building's pad. Item names: wheat, flour, bread. All queries cost no ticks, but consume interpreter operations.</p><pre>navigate_to("mill")\nwhile stored("mill", "flour") == 0:\n    wait()\nload("flour", 1)\nnavigate_to("oven")\nunload("flour", 1)</pre><p>This waiting example assumes you already supplied wheat to the mill. A waiting loop cannot create missing ingredients.</p>`;
}
