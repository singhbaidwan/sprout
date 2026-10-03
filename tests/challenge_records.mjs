// The record marker must survive reload without counting a result twice.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync(new URL('../static/challenges-ui.js', import.meta.url), 'utf8');
const {recordChallenge} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const save = {trial: {recorded: false}};
const state = {challenge: {id: 'rush', drones: 1, status: 'complete'}, tick: 143,
  stats: {bread_delivered: 12}, efficiency: {water_used: 0, moves: 118, empty_moves: 84}};
assert.equal(recordChallenge(save, state), true);
const restored = JSON.parse(JSON.stringify(save));
assert.equal(recordChallenge(restored, state), false);
assert.equal(restored.challenge_records['rush:1'].attempts, 1);
restored.trial.recorded = false;
recordChallenge(restored, {...state, tick: 120});
assert.equal(restored.challenge_records['rush:1'].best.ticks, 120);
assert.equal(restored.challenge_records['rush:1'].previous.ticks, 143);
restored.trial.recorded = false;
recordChallenge(restored, {...state, challenge: {...state.challenge, status: 'failed'}, tick: 180});
assert.equal(restored.challenge_records['rush:1'].last.status, 'failed');
assert.equal(restored.challenge_records['rush:1'].best.ticks, 120);
restored.trial.recorded = false;
recordChallenge(restored, {...state, challenge: {...state.challenge, drones: 2}, tick: 130});
assert.equal(restored.challenge_records['rush:2'].attempts, 1);
assert.equal(restored.challenge_records['rush:1'].attempts, 3);
console.log('Challenge record persistence, ranking, and team separation passed.');
