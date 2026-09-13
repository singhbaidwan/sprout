import { FarmRenderer } from './farm.js';

const $ = id => document.getElementById(id);
const STORAGE_KEY = 'sprout.save.v2';
const editor = $('code-editor');
let state, crops, missions, examples, initialState;
let mode = 'loading', queue = [], queueIndex = 0, resultError = null;
let timer = null, toastTimer = null, saveTimer = null, requestToken = 0, controller = null;
let currentLine = null, errorLine = null, selected = null, logs = 0;
let storageAvailable = true;
let saveData = { format: 'sprout-save', version: 2, active: 'classic', games: {} }, pendingImport = null;

const renderer = new FarmRenderer($('farm-canvas'), (x, y) => { selected = { x, y }; updateInspector(); });
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

async function api(path, payload, signal) {
  const response = await fetch(`/api/${path}`, payload === undefined ? { signal } : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal,
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || 'The farm could not process that request.');
    error.status = response.status;
    throw error;
  }
  return data;
}

function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').classList.toggle('error', error);
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4200);
}

function log(message, kind = 'info', line = null) {
  const row = document.createElement('div'); row.className = `log-line ${kind}`;
  const stamp = document.createElement('span'); stamp.className = 'log-time';
  stamp.textContent = line ? `L${String(line).padStart(2, '0')}` : 'SYS';
  const content = document.createElement('span'); content.className = 'log-message'; content.textContent = message;
  row.append(stamp, content); $('console').append(row);
  while ($('console').children.length > 150) $('console').firstChild.remove();
  $('console').scrollTop = $('console').scrollHeight;
  $('log-count').textContent = String(++logs);
}

function save() {
  if (!state) return;
  saveData.games[saveData.active] = { state, code: editor.value, speed: $('speed-select').value };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saveData));
    $('save-status').textContent = 'Saved on this device';
  } catch {
    $('save-status').textContent = 'Saving unavailable';
    if (storageAvailable) { storageAvailable = false; toast('Browser storage is unavailable. This farm will last for this tab only.', true); }
  }
}

function codeHighlight() {
  const source = editor.value;
  const tokens = /(#.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:def|for|in|while|if|else|elif|return|break|continue|and|or|not|is|pass|True|False|None)\b|\b\d+(?:\.\d+)?\b|\b[a-zA-Z_]\w*(?=\())/gm;
  let html = '', last = 0;
  for (const match of source.matchAll(tokens)) {
    html += escapeHTML(source.slice(last, match.index));
    const value = match[0];
    const kind = value.startsWith('#') ? 'comment' : /^["']/.test(value) ? 'string' : /^\d/.test(value) ? 'number' : /^(def|for|in|while|if|else|elif|return|break|continue|and|or|not|is|pass|True|False|None)$/.test(value) ? 'keyword' : 'function';
    html += `<span class="token-${kind}">${escapeHTML(value)}</span>`;
    last = match.index + value.length;
  }
  $('code-highlight').firstElementChild.innerHTML = html + escapeHTML(source.slice(last)) + '\n';
  updateLines(); syncScroll(); cursorPosition();
}

function updateLines() {
  $('line-numbers').replaceChildren();
  const count = editor.value.split('\n').length;
  const fragment = document.createDocumentFragment();
  for (let i = 1; i <= count; i++) {
    const line = document.createElement('div'); line.className = 'line-number'; line.textContent = i;
    line.classList.toggle('current', i === currentLine); line.classList.toggle('error-line', i === errorLine);
    fragment.append(line);
  }
  $('line-numbers').append(fragment);
  $('line-numbers').scrollTop = editor.scrollTop;
}

function syncScroll() {
  $('code-highlight').scrollTop = editor.scrollTop;
  $('code-highlight').scrollLeft = editor.scrollLeft;
  $('line-numbers').scrollTop = editor.scrollTop;
}

function cursorPosition() {
  const before = editor.value.slice(0, editor.selectionStart).split('\n');
  $('cursor-position').textContent = `Ln ${before.length}, Col ${before.at(-1).length + 1}`;
}

function setCode(code) {
  editor.value = code; editor.scrollTop = 0; editor.scrollLeft = 0; editor.setSelectionRange(0, 0);
  currentLine = errorLine = null; codeHighlight();
}

function setMode(next, label) {
  mode = next;
  const busy = ['running', 'paused', 'loading'].includes(mode);
  editor.readOnly = busy;
  $('example-select').disabled = busy;
  $('run-button').disabled = mode === 'loading' || !state;
  $('run-label').textContent = mode === 'running' ? 'Pause' : mode === 'paused' ? 'Resume' : mode === 'loading' ? 'Preparing…' : 'Run code';
  $('run-symbol').textContent = mode === 'running' ? 'Ⅱ' : '▶';
  $('step-button').disabled = mode === 'running' || mode === 'loading' || !state;
  $('stop-button').disabled = !busy || !state;
  $('reset-open').disabled = $('reset-footer').disabled = $('reset-confirm').disabled = !state;
  $('export-save').disabled = !state;
  $('import-save').disabled = busy || !state;
  $('runtime-status').textContent = label || ({ idle: 'Ready when you are', paused: 'Paused · step or resume', running: 'Program running', loading: 'Preparing your program', error: 'Check your program' }[mode]);
  $('runtime-dot').className = `status-dot ${mode === 'running' ? 'running' : mode === 'error' ? 'error' : ''}`;
  $('field-status').textContent = mode === 'running' ? 'Drone working' : mode === 'paused' ? 'Drone paused' : 'Drone ready';
  if (state) updateUpgrades();
}

function updateState(next, action = null) {
  state = next;
  $('coins').textContent = state.coins.toLocaleString();
  $('harvests').textContent = state.stats.harvested.toLocaleString();
  $('ticks').textContent = state.tick.toLocaleString();
  $('field-size').textContent = `${state.size} × ${state.size}`;
  $('drone-position').textContent = `x: ${state.drone.x}   y: ${state.drone.y}`;
  renderer.update(state, action);
  updateInspector(); updateMission(); updateUpgrades();
}

function tileDescription(tile) {
  if (!tile.crop) return tile.tilled ? (tile.water ? 'Prepared soil · watered' : 'Prepared soil · ready to plant') : 'Grass · needs tilling';
  const ripe = tile.growth >= crops[tile.crop].growth;
  return `${tile.crop[0].toUpperCase() + tile.crop.slice(1)} · ${ripe ? 'ready to harvest' : `${Math.round(tile.growth / crops[tile.crop].growth * 100)}% grown · ${tile.water ? 'watered' : 'needs water'}`}`;
}

function updateInspector() {
  if (!state) return;
  if (selected && (selected.x >= state.size || selected.y >= state.size)) selected = null;
  const { x, y } = selected || state.drone;
  $('tile-title').textContent = `Plot ${x}, ${y}${x === state.drone.x && y === state.drone.y ? ' · drone here' : ''}`;
  $('tile-detail').textContent = tileDescription(state.tiles[y * state.size + x]);
}

function updateMission() {
  const tips = [
    'Your first three wheat plots are ready. Press Run code to bring in your first harvest.',
    'Ready for more? Load “The whole field” and use nested loops to plant every row.',
    'Unlock carrots, then load “A carrot patch” to try your new crop.',
    'A good routine pays off. Run “Harvest & replant” to keep your farm growing.',
    'The farm is yours. Experiment with new crops, larger fields, and more efficient programs.',
  ];
  document.querySelector('.editor-tip p').textContent = tips[Math.min(state.completed.length, 4)];
  const mission = missions[state.completed.length];
  if (!mission) {
    $('mission-number').textContent = 'ALL 4 MISSIONS COMPLETE';
    $('mission-title').textContent = 'You grew an idea into a farm.';
    $('mission-description').textContent = 'Keep experimenting. How efficient can your next harvest be?';
    $('mission-reward').textContent = 'Sandbox unlocked';
    $('mission-progress').max = 4; $('mission-progress').value = 4; $('mission-count').textContent = '4 / 4';
    return;
  }
  const progress = Math.min(state.stats[mission.stat], mission.target);
  $('mission-number').textContent = `MISSION ${String(state.completed.length + 1).padStart(2, '0')} / 04`;
  $('mission-title').textContent = mission.title; $('mission-description').textContent = mission.description;
  $('mission-reward').textContent = `+${mission.reward} coins`;
  $('mission-progress').max = mission.target; $('mission-progress').value = progress;
  $('mission-count').textContent = `${progress} / ${mission.target}`;
}

const upgradeItems = [
  { id: 'carrot', title: 'Carrots', detail: 'A sweeter return', cost: 40, art: '<path d="m12 10 9 7-15 10Z" fill="#d69c63"/><path d="m18 11 1-7m0 8 7-6m-7 7 9-1" stroke="#8eaa66" stroke-width="3" stroke-linecap="round"/><path d="m10 15 3 2m-5 4 2 1" stroke="#b98050" stroke-width="1.5"/>' },
  { id: 'sunflower', title: 'Sunflowers', detail: 'A brighter harvest', cost: 100, art: '<path d="M16 17v13m0-7-7-4m7 7 7-5" stroke="#91a364" stroke-width="2.5"/><path d="m16 3 3 4 5-1 0 5 5 3-4 4 1 5-6-1-4 4-3-5-5 0 1-5-4-4 5-2 1-5Z" fill="#dec579"/><circle cx="16" cy="14" r="5" fill="#9a8760"/>' },
  { id: 'expansion', title: 'More land', detail: 'Expand to 8 × 8', cost: 150, art: '<path d="m16 5 13 7-13 7L3 12Z" fill="#bbcc91"/><path d="m3 12 13 7 13-7v6l-13 8L3 18Z" fill="#a1b67e"/><path d="m10 9 13 7m-1-7-13 7" stroke="#ecf0d4"/><path d="M16 20v10m-4-5 4 5 4-5" stroke="#819661" stroke-width="2" fill="none"/>' },
];

function createUpgrades() {
  $('upgrade-list').innerHTML = upgradeItems.map(item => `<article class="upgrade-card" id="upgrade-${item.id}"><div class="upgrade-art" aria-hidden="true"><svg viewBox="0 0 32 32">${item.art}</svg></div><div><h3 class="upgrade-title">${item.title}</h3><p class="upgrade-detail">${item.detail}</p></div><button data-upgrade="${item.id}"></button></article>`).join('');
  document.querySelectorAll('[data-upgrade]').forEach(button => button.addEventListener('click', () => unlock(button.dataset.upgrade)));
}

function updateUpgrades() {
  for (const item of upgradeItems) {
    const card = $(`upgrade-${item.id}`); if (!card) continue;
    const unlocked = item.id === 'expansion' ? state.size === 8 : state.unlocked.includes(item.id);
    const button = card.querySelector('button');
    card.classList.toggle('unlocked', unlocked);
    button.disabled = unlocked || state.coins < item.cost || ['running', 'paused', 'loading'].includes(mode);
    button.textContent = unlocked ? '✓ Unlocked' : `Unlock · ${item.cost} coins`;
    button.title = unlocked ? 'Already unlocked' : state.coins < item.cost ? `${item.cost - state.coins} more coins needed` : `Unlock ${item.title}`;
    button.setAttribute('aria-label', unlocked ? `${item.title} unlocked` : `Unlock ${item.title} for ${item.cost} coins`);
  }
}

async function unlock(item) {
  if (!['idle', 'error'].includes(mode)) return;
  const token = ++requestToken;
  controller = new AbortController();
  setMode('loading', 'Opening the workshop…');
  try {
    const result = await api('unlock', { state, item }, controller.signal);
    if (token !== requestToken) return;
    updateState(result.state); save(); log(result.message, 'success'); toast(result.message); setMode('idle');
  } catch (error) {
    if (token !== requestToken) return;
    log(error.message, 'error'); toast(error.message, true); setMode('error', 'Workshop request failed');
  }
}

async function prepare(singleStep = false) {
  if (!state || mode === 'loading') return;
  const token = ++requestToken;
  controller = new AbortController();
  currentLine = errorLine = null; updateLines();
  setMode('loading'); save();
  try {
    const result = await api('run', { state, code: editor.value }, controller.signal);
    if (token !== requestToken) return;
    queue = result.frames; queueIndex = 0; resultError = result.error;
    log(`Program prepared · ${result.actions} drone action${result.actions === 1 ? '' : 's'}`);
    setMode(singleStep ? 'paused' : 'running');
    if (singleStep) advanceOne(); else play();
  } catch (error) {
    if (token !== requestToken) return;
    const message = error instanceof TypeError ? 'Cannot reach Python. Start python3 run.py, then try again.' : error.message;
    log(message, 'error'); toast(message, true); setMode('error', 'Could not reach the farm');
  }
}

function applyFrame(frame) {
  currentLine = frame.line; updateLines();
  if (frame.state) {
    updateState(frame.state, frame.action); save();
    $('action-status').textContent = frame.message;
  }
  log(frame.message, frame.kind === 'output' ? 'output' : frame.action === 'harvest' ? 'success' : 'info', frame.line);
  for (const message of frame.events || []) { log(message, 'success'); toast(message); }
}

function finish() {
  clearTimeout(timer); timer = null;
  currentLine = null;
  if (resultError) {
    errorLine = resultError.line;
    log(`${resultError.line ? `Line ${resultError.line}: ` : ''}${resultError.message}`, 'error');
    setMode('error', resultError.line ? `Error on line ${resultError.line}` : 'Check your program');
    toast(resultError.message, true);
  } else { log('Program finished. Ready for your next idea.', 'success'); setMode('idle', 'Program complete'); }
  queue = []; queueIndex = 0; resultError = null; updateLines(); save();
}

function advanceOne() {
  while (queueIndex < queue.length) {
    const frame = queue[queueIndex++]; applyFrame(frame);
    if (frame.state) break;
  }
  // Output after the final action does not require a redundant extra click.
  if (!queue.slice(queueIndex).some(frame => frame.state)) {
    while (queueIndex < queue.length) applyFrame(queue[queueIndex++]);
    finish();
  } else if (mode === 'paused') $('runtime-status').textContent = `Paused · tick ${state.tick}`;
}

function play() {
  if (mode !== 'running') return;
  advanceOne();
  if (mode === 'running') timer = setTimeout(play, 560 / Number($('speed-select').value));
}

function stop(silent = false) {
  ++requestToken; controller?.abort();
  clearTimeout(timer); timer = null;
  queue = []; queueIndex = 0; resultError = null; currentLine = null;
  setMode('idle', 'Stopped · farm progress kept'); updateLines(); save();
  if (!silent) log('Stopped. Only completed actions have been kept.');
}

function openGuide(tab = 'learn') {
  renderGuide(tab);
  if (!$('guide-dialog').open) $('guide-dialog').showModal();
}

function renderGuide(tab) {
  document.querySelectorAll('.guide-tab').forEach(button => button.classList.toggle('active', button.dataset.guide === tab));
  const content = {
    learn: `<p>You have a small patch of land, a solar-powered drone, and a Python editor. A good routine is all your farm needs.</p><ol><li><strong>Make your first harvest.</strong> The first three plots have ripe wheat. Run the starter program to harvest them, replant the row, and earn your first mission reward.</li><li><strong>Grow a crop.</strong> Use <code>till()</code>, <code>plant("wheat")</code>, then <code>water()</code>. Crops grow when the drone takes actions. Use <code>wait()</code> if you have nothing else to do.</li><li><strong>Think in loops.</strong> Load “The whole field” to plant every plot. Load “Harvest & replant” to maintain it. Each run continues from your current farm state.</li><li><strong>Make room to grow.</strong> Spend coins on carrots, sunflowers, and more land. Complete all four missions, then experiment freely.</li></ol><h3>You're in control</h3><p><strong>Run code</strong> starts or resumes a program. <strong>Pause</strong> freezes it. <strong>Step</strong> performs one drone action. <strong>Stop</strong> discards the remaining actions and keeps the changes you have already seen. Speed changes the animation, not crop growth rules.</p><h3>A few helpful details</h3><p>The field wraps at its edges. North decreases y; east increases x. Time only passes during actions. There is no battery or water refill to manage, and wheat has a free emergency seed if you run out of coins. Your farm and editor save on this device.</p><p>Use <strong>Ctrl/Cmd + Enter</strong> to run or pause, <strong>Tab</strong> for four spaces, and <strong>Shift + Tab</strong> to unindent. Select a tile or use Inspect plots to learn what it needs.</p>`,
    api: `<p>Farm Python is a bounded subset of Python. It supports variables, math, lists, indexing, <code>if</code>, <code>for</code>, <code>while</code>, <code>def</code>, <code>return</code>, <code>break</code>, and <code>continue</code>. Imports, attributes, packages, comprehensions, and file access are unavailable.</p><h3>Drone commands · each takes one tick</h3><table><thead><tr><th>Command</th><th>What it does</th></tr></thead><tbody><tr><td><code>move("east")</code></td><td>Move one plot. Also north, south, west. Edges wrap.</td></tr><tr><td><code>till()</code></td><td>Prepare an empty plot for planting.</td></tr><tr><td><code>plant("wheat")</code></td><td>Spend coins on a seed. Also carrot or sunflower after unlocking.</td></tr><tr><td><code>water()</code></td><td>Give this plot 24 ticks of moisture, including this action's tick.</td></tr><tr><td><code>harvest()</code></td><td>Sell a ripe crop. The soil stays tilled.</td></tr><tr><td><code>wait()</code></td><td>Let one tick pass without moving.</td></tr></tbody></table><h3>Queries · no time passes</h3><p><code>can_harvest()</code> → boolean<br><code>get_crop()</code> → crop name or None<br><code>get_water()</code> → remaining moisture ticks<br><code>is_tilled()</code> → boolean<br><code>get_x()</code>, <code>get_y()</code> → drone coordinates<br><code>get_size()</code> → field width (6 or 8)<br><code>get_coins()</code> → current balance</p><h3>Python helpers</h3><p><code>range()</code>, <code>len()</code>, <code>min()</code>, <code>max()</code>, <code>abs()</code>, <code>int()</code>, <code>str()</code>, and <code>print()</code>. Functions use positional arguments. Lists are read-only; build a new list to change one.</p><pre>while not can_harvest():\n    if get_water() == 0:\n        water()\n    else:\n        wait()\nharvest()</pre><p>Each run allows up to 400 drone actions and 20,000 interpreter operations. Large or infinite programs stop with a useful error; already-played actions remain. Run another cycle to continue.</p>`,
    crops: `<p>Plant seeds with your harvest income. Watered crops grow one stage per drone action. Mature crops stay ready indefinitely.</p><table><thead><tr><th>Crop</th><th>Seed</th><th>Sale</th><th>Growth</th><th>Unlock</th></tr></thead><tbody>${Object.entries(crops || {}).map(([name, crop]) => `<tr><td>${escapeHTML(name)}</td><td>${crop.seed}</td><td>${crop.sale}</td><td>${crop.growth} ticks</td><td>${crop.unlock || 'Free'}</td></tr>`).join('')}</tbody></table><h3>Four milestones</h3><ol>${(missions || []).map(mission => `<li><strong>${escapeHTML(mission.title)}</strong><br>${escapeHTML(mission.description)} Reward: ${mission.reward} coins.</li>`).join('')}</ol><p>Mission rewards arrive automatically, in order. Lifetime crop sales count toward the final mission; mission rewards do not. More land costs 150 coins and expands your farm to 8 × 8 without removing crops.</p><h3>Your next challenge</h3><p>Finish the missions, unlock every crop, and expand the field. Then try earning more coins with fewer drone actions. The game remains open for experimentation.</p>`,
  };
  $('guide-content').innerHTML = content[tab] || content.learn;
}

function showPlots() {
  if (!state) return;
  const rows = state.tiles.map((tile, index) => {
    const x = index % state.size, y = Math.floor(index / state.size), here = x === state.drone.x && y === state.drone.y;
    return `<tr class="${here ? 'current' : ''}"><td>${x}, ${y}${here ? ' · drone' : ''}</td><td>${escapeHTML(tileDescription(tile))}</td><td>${tile.water} ticks</td></tr>`;
  });
  $('plots-table').innerHTML = `<table><thead><tr><th>Plot</th><th>Crop / soil</th><th>Moisture</th></tr></thead><tbody>${rows.join('')}</tbody></table>`;
  $('plots-dialog').showModal();
}

function runOrPause() {
  if (mode === 'running') { clearTimeout(timer); setMode('paused'); }
  else if (mode === 'paused') { setMode('running'); play(); }
  else if (mode !== 'loading') prepare();
}

$('run-button').addEventListener('click', runOrPause);
$('step-button').addEventListener('click', () => mode === 'paused' ? advanceOne() : prepare(true));
$('stop-button').addEventListener('click', () => stop());
$('speed-select').addEventListener('change', save);
$('clear-log').addEventListener('click', () => { $('console').replaceChildren(); logs = 0; $('log-count').textContent = '0'; });
$('example-select').addEventListener('change', event => {
  const value = event.target.value;
  if (examples?.[value]) { setCode(examples[value]); setMode('idle'); save(); log('Example loaded. It will run from your current farm state.'); toast('Example loaded. Make it your own.'); }
  event.target.value = '';
});

editor.addEventListener('input', () => { errorLine = null; codeHighlight(); clearTimeout(saveTimer); saveTimer = setTimeout(save, 300); });
editor.addEventListener('scroll', syncScroll);
editor.addEventListener('click', cursorPosition); editor.addEventListener('keyup', cursorPosition);
editor.addEventListener('keydown', event => {
  if (editor.readOnly || event.ctrlKey || event.metaKey) return;
  const start = editor.selectionStart, end = editor.selectionEnd;
  if (event.key === 'Tab') {
    event.preventDefault();
    const lineStart = editor.value.lastIndexOf('\n', start - 1) + 1;
    if (start !== end || event.shiftKey) {
      const text = editor.value.slice(lineStart, end);
      const transformed = text.split('\n').map(line => event.shiftKey ? line.replace(/^ {1,4}/, '') : `    ${line}`).join('\n');
      editor.setRangeText(transformed, lineStart, end, 'select');
    } else editor.setRangeText('    ', start, end, 'end');
    editor.dispatchEvent(new Event('input'));
  } else if (event.key === 'Enter') {
    event.preventDefault();
    const line = editor.value.slice(0, start).split('\n').at(-1);
    const indent = line.match(/^ */)[0] + (line.trimEnd().endsWith(':') ? '    ' : '');
    editor.setRangeText(`\n${indent}`, start, end, 'end');
    editor.dispatchEvent(new Event('input'));
  }
});
document.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !document.querySelector('dialog[open]')) { event.preventDefault(); runOrPause(); }
});
window.addEventListener('pagehide', save);

$('export-save').addEventListener('click', () => {
  save();
  const url = URL.createObjectURL(new Blob([JSON.stringify(saveData, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url;
  link.download = `sprout-${new Date().toISOString().slice(0, 10)}.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('Save exported. Keep it somewhere safe.');
});
$('import-save').addEventListener('click', () => $('save-file').click());
$('save-file').addEventListener('change', async event => {
  const file = event.target.files[0]; event.target.value = ''; pendingImport = null;
  if (!file) return;
  setMode('loading', 'Checking save…');
  try {
    if (file.size > 90000) throw new Error('Save files must be under 90 KB.');
    const result = await api('save/validate', { save: JSON.parse(await file.text()) });
    pendingImport = result.save;
    const game = pendingImport.games[pendingImport.active];
    $('import-summary').textContent = `${Object.keys(pendingImport.games).length} chapter(s), ${game.state.coins} coins, tick ${game.state.tick}. This replaces the saved chapters on this device.`;
    $('import-dialog').showModal();
  } catch (error) { toast(`Save not imported: ${error.message}`, true); }
  finally { setMode('idle'); }
});
$('import-confirm').addEventListener('click', () => {
  if (!pendingImport) return;
  save();
  try { localStorage.setItem('sprout.save.backup', JSON.stringify(saveData)); }
  catch { toast('Could not back up your current save. Export it before importing.', true); return; }
  stop(true); saveData = pendingImport; pendingImport = null;
  const game = saveData.games[saveData.active];
  selected = renderer.selected = null;
  setCode(game.code); $('speed-select').value = game.speed; updateState(game.state); save();
  $('import-dialog').close(); toast('Save restored.');
});

$('api-open').addEventListener('click', () => openGuide('api'));
$('guide-top').addEventListener('click', () => openGuide());
$('footer-guide').addEventListener('click', () => openGuide('api'));
$('farm-tab').addEventListener('click', () => $('farm-canvas').focus());
$('mission-hint').addEventListener('click', () => {
  const hints = ['Run the starter example to harvest the three ripe wheat plots.', 'Load “The whole field” to plant more rows with nested loops.', 'Unlock carrots for 40 coins, then load “A carrot patch”.', 'Run “Harvest & replant” for repeated harvest income.'];
  toast(hints[state?.completed.length] || 'Try growing sunflowers across your expanded farm.');
});
$('inspect-plots').addEventListener('click', showPlots);
$('reset-open').addEventListener('click', () => $('reset-dialog').showModal());
$('reset-footer').addEventListener('click', () => $('reset-dialog').showModal());
$('reset-confirm').addEventListener('click', () => {
  stop(true); selected = null; renderer.selected = null;
  updateState(structuredClone(initialState)); setCode(examples.starter); setMode('idle');
  $('action-status').textContent = 'Ready for your first command';
  $('console').replaceChildren(); logs = 0;
  log('A fresh patch of possibility. Welcome back.', 'success'); save();
  $('reset-dialog').close(); toast('Your new farm is ready.');
});
document.querySelectorAll('.close-dialog').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
document.querySelectorAll('.guide-tab').forEach(button => button.addEventListener('click', () => renderGuide(button.dataset.guide)));

async function boot() {
  try {
    const data = await api('bootstrap');
    crops = data.crops; missions = data.missions; examples = data.examples; initialState = structuredClone(data.state);
    let restored = data.state, code = examples.starter, restoreMessage = null;
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || localStorage.getItem('sprout.save.v1') || 'null');
      if (saved) {
        const valid = await api('save/validate', { save: saved });
        saveData = valid.save;
        const game = saveData.games[saveData.active];
        restored = game.state; code = game.code; $('speed-select').value = game.speed;
        restoreMessage = 'Welcome back. Your farm and program have been restored.';
      }
    } catch (error) {
      // A transport failure must not overwrite an otherwise valid existing save.
      if (error instanceof TypeError || (error.status && error.status !== 400)) throw error;
      restoreMessage = `Could not restore saved progress: ${error.message}. A fresh farm is ready.`;
      toast(restoreMessage, true);
    }
    createUpgrades(); setCode(code); updateState(restored); setMode('idle');
    log(restoreMessage || 'Drone connected. Your first harvest is one program away.', 'success');
    log(restoreMessage ? 'Your next run continues from this field. Load an example for ideas.' : 'Tip: press Run code to try the starter program.');
    save();
  } catch (error) {
    $('connection-error').hidden = false;
    $('connection-error').textContent = 'Could not load your farm. Keep python3 run.py running, then reload this page.';
    $('runtime-status').textContent = 'Python connection unavailable';
    $('save-status').textContent = 'Farm unavailable';
    log(error.message, 'error');
  }
}

setMode('loading', 'Connecting to Python…');
boot();
