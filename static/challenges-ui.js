const $ = id => document.getElementById(id);
let rules = {};
export const terminalChallenge = state => Boolean(state?.challenge && state.challenge.status !== 'active');

export function setupChallenges(catalog) {
  rules = catalog;
  $('challenge-select').replaceChildren(...Object.entries(rules).map(([id, rule]) => new Option(rule.title, id)));
  $('challenge-select').addEventListener('change', describeSelection);
  describeSelection();
}

function describeSelection() {
  const rule = rules[$('challenge-select').value];
  if (!rule) return;
  $('challenge-description').textContent = `${rule.description} ${rule.deadline} ticks${rule.water_budget === null ? '' : ` · ${rule.water_budget} tank water maximum`}.`;
}

// Records belong to the save envelope, outside the checkpoint-bound world.
export function recordChallenge(save, state) {
  if (!terminalChallenge(state) || save.trial.recorded) return false;
  const metrics = state.efficiency, challenge = state.challenge;
  const score = {status: challenge.status, ticks: state.tick, delivered: state.stats.bread_delivered,
    water_used: metrics.water_used, moves: metrics.moves, empty_moves: metrics.empty_moves};
  const key = `${challenge.id}:${challenge.drones}`;
  const records = save.challenge_records ||= {};
  const entry = records[key] ||= {attempts: 0, best: null, last: null, previous: null};
  const better = !entry.best || score.ticks < entry.best.ticks || score.ticks === entry.best.ticks &&
    (score.water_used < entry.best.water_used || score.water_used === entry.best.water_used && score.empty_moves < entry.best.empty_moves);
  entry.attempts++; entry.previous = entry.last; entry.last = score;
  if (score.status === 'complete' && better) entry.best = {...score};
  save.trial.recorded = true;
  return true;
}

export function updateOptimization(state, save, busy) {
  const factory = state?.scenario === 'factory', trial = Boolean(state?.challenge);
  $('challenge-panel').hidden = $('efficiency-panel').hidden = !factory;
  if (!factory) return;
  const challenge = state.challenge;
  if (trial) {
    $('challenge-select').value = challenge.id;
    $('challenge-drones').value = String(challenge.drones);
  }
  describeSelection();
  $('challenge-select').disabled = $('challenge-drones').disabled = busy || trial;
  $('challenge-start').disabled = busy;
  $('challenge-start').textContent = trial ? 'Retry with my code' : 'Start challenge';
  $('challenge-resume').hidden = trial || !save.trial;
  $('challenge-resume').disabled = busy;
  $('challenge-return').hidden = !trial;
  $('challenge-return').disabled = busy;
  $('challenge-progress').hidden = !trial;
  $('challenge-note').textContent = trial ? 'Fixed growing rules and equipment. Stop to edit or retry; Return to farm restores your campaign.' : 'A separate farm with fixed starting conditions. Your campaign and code are kept. Starter programs included.';
  if (trial) {
    const rule = rules[challenge.id];
    $('challenge-status').textContent = challenge.status === 'active' ? `${rule.title} · attempt in progress` : challenge.status === 'complete' ? `${rule.title} · completed!` : `${rule.title} · budget reached`;
    $('challenge-target').textContent = `${state.stats.bread_delivered} / ${rule.target} bread · ${state.tick} / ${rule.deadline} ticks${rule.water_budget === null ? '' : ` · ${state.efficiency.water_used} / ${rule.water_budget} water`}`;
    $('challenge-goal').max = rule.target; $('challenge-goal').value = state.stats.bread_delivered;
  }
  const key = `${$('challenge-select').value}:${$('challenge-drones').value}`;
  const entry = save.challenge_records?.[key];
  const best = entry?.best;
  let record = best ? `Best: ${best.ticks} ticks · ${best.water_used} water · ${best.empty_moves} empty moves` : 'No completed record yet. Try the starter, then improve its routes.';
  if (entry?.last) {
    record += ` · ${entry.attempts} resolved attempt${entry.attempts === 1 ? '' : 's'}. Last: ${entry.last.status}, ${entry.last.ticks} ticks`;
    if (entry.previous?.status === 'complete' && entry.last.status === 'complete') {
      const delta = field => `${entry.last[field] - entry.previous[field] >= 0 ? '+' : ''}${entry.last[field] - entry.previous[field]}`;
      record += `. vs previous: ${delta('ticks')} ticks, ${delta('water_used')} water, ${delta('empty_moves')} empty moves`;
    }
  }
  $('challenge-record').textContent = record;

  const m = state.efficiency;
  const ticks = m?.ticks || 0, delivered = m ? state.stats.bread_delivered - m.start_delivered : 0;
  $('efficiency-window').textContent = m ? `${ticks} shared tick${ticks === 1 ? '' : 's'} · ${m.commands} drone command${m.commands === 1 ? '' : 's'} · since tick ${m.start_tick}` : 'Measurement starts with your next action.';
  $('metric-throughput').textContent = ticks ? (delivered * 100 / ticks).toFixed(1) : '—';
  $('metric-water').textContent = delivered ? (m.water_used / delivered).toFixed(1) : '—';
  $('metric-travel').textContent = m?.moves ? `${Math.round(m.empty_moves * 100 / m.moves)}%` : '—';
  $('metric-activity').textContent = `${m?.waits || 0} waits · ${m?.transfers || 0} transfers · ${m?.water_used || 0} tank water`;
  $('metric-water-label').textContent = state.care.settings.irrigation ? 'tank water / loaf' : 'tank water / loaf · irrigation off';
  for (const name of ['mill', 'oven']) {
    const machine = m?.machines[name] || {working: 0, starved: 0, output_full: 0};
    for (const bucket of ['working', 'starved', 'output_full']) {
      const percent = ticks ? Math.round(machine[bucket] * 100 / ticks) : 0;
      $(`${name}-${bucket}`).style.width = `${ticks ? machine[bucket] * 100 / ticks : 0}%`;
      $(`${name}-${bucket}`).title = `${bucket}: ${machine[bucket]} ticks`;
      $(`${name}-${bucket}-value`).textContent = `${percent}%`;
    }
  }
  const waits = ['mill', 'oven'].flatMap(name => ['starved', 'output_full'].map(reason => ({name, reason, ticks: m?.machines[name][reason] || 0}))).sort((a,b) => b.ticks - a.ticks);
  $('efficiency-hint').textContent = !ticks ? 'Run a program to find where production waits.' : waits[0].ticks === 0 ? 'Both machines are busy. Check delivery routes and empty travel next.' :
    `${waits[0].name === 'mill' ? 'Mill' : 'Oven'} ${waits[0].reason === 'starved' ? 'waits most for input. Keep its supply buffer stocked.' : 'waits most for output space. Collect its products sooner.'}`;
  $('efficiency-reset').disabled = busy || trial;
}
