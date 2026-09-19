# Continuous automation

Implemented in the Stage 3 milestone, 2026-09-20. Both chapters support **Bounded run** and **Continuous** modes.

## Play it

1. Open either chapter and load **Continuous autopilot**. Loading this example selects Continuous mode automatically.
2. Press **Run code**. Home farm maintains six wheat plots. Breadworks tends crops, moves wheat and flour, and delivers bread in a repeating production loop.
3. Enable any growing options before starting; these examples check fertilizer, compost, irrigation supplies, and actual harvest yield.
4. **Pause** freezes the displayed world. **Step** advances at most one drone action. **Resume** continues the same function, loop, and variables.
5. **Stop** keeps the farm and clears the controller. You can then edit code, change options, buy upgrades, start an order, or switch chapters.

A script only repeats if you write a loop. Finite scripts finish in Continuous mode too. Start from the provided examples, or try this on a Home farm plot with a growing crop:

```python
while True:
    if can_harvest():
        harvest()
    if get_crop() == None:
        till()
        plant("wheat")
    if get_water() < 6:
        water()
    else:
        wait()
```

This small fragment assumes Irrigation is off; the full autopilot examples include supply checks. The example controllers are starting points for optimization, not guaranteed solutions for every manually arranged inventory or timed order.

## Clock and controls

Every successful action applies its effect and advances the shared crop, irrigation, machine, and order clock once. Queries, calculations, printing, Pause, and wall-clock waiting do not advance time. A route yields after **each tile**, including inside functions or expressions.

The browser requests one action at a time. Pause/Stop invalidate an outstanding response and keep the last displayed action. The server has no mutable farm session, so an ignored calculation cannot advance your saved farm. Speed changes the delay between requests, not simulation rules. Network interruptions leave the last checkpoint paused; Resume retries from that exact point.

There is no offline growth, background server worker, automatic restart after completion, or execution while the page is closed. Background-tab throttling can reduce real-world speed without changing outcomes.

## Saves and recovery

World and controller save together after every displayed action. Reload, server restart, and a valid imported save restore the controller **paused**. Resume continues without replaying earlier actions. Stop deliberately discards program position and variables, retaining farm progress. A bounded run still restores only displayed world progress after reload.

The portable version 2 save envelope adds optional per-chapter fields:

- `execution`: `"finite"` (the default for old saves) or `"continuous"`.
- `checkpoint`: version 1 continuation containing instruction position, locals/globals, expression values, call/loop stacks, unfinished navigation, and a revision.

Checkpoints are bound to source and validated world using SHA-256 digests. Changing code/world independently makes the pair invalid. Digests detect mismatches; they are not signatures or anti-cheat protection. They require no local secret and work across devices and server restarts. The compiled instructions are regenerated from validated source and are never imported from a save.

Save files may be up to 590 KB; the save-validation and controller endpoints allow 600,000 bytes including the request envelope. Other endpoints retain their 100,000-byte limit. Export uses compact JSON to keep two chapters and checkpoints within the limit. Multiple browser tabs still use last-write-wins storage; use one tab per saved farm.

## Execution bounds

| Resource | Bounded run | Continuous |
| --- | --- | --- |
| Drone actions | 400 per run | One per request; no 400-action run cap |
| Interpreter work | 20,000 operations per run | 20,000 operations before the next action or completion |
| Output | 100 messages per run | 100 messages between actions |
| Controller persistence | World only | World plus up to 48 KB of checkpoint data |
| Call depth | 24 user calls | 24 user calls |
| Source, AST, values | Existing bounded subset | Same source/AST/numeric/collection bounds |

The two interpreters count internal operations differently; the quotas are work limits, not a common performance score. Continuous expression values and encoded objects are capped at 2,500, and active for-loop records at 256. Checkpoints use typed values and bounded references to preserve aliases; cyclic or forward references are rejected.

`while True: pass` stops with a useful error instead of freezing. A polling loop must include `wait()` or another action. No imports, attributes, host Python execution, files, packages, or new player API functions are introduced.

## Transport and future extension

`POST /api/controller/step` accepts `{state, code, checkpoint}`; omit or use null for a new controller. It returns `{frames, state, checkpoint, revision, done, error, actions, operations}`. A completion/error response has no continuation. Invalid incoming state/checkpoints are HTTP 400; player script failures are line-aware errors in HTTP 200 responses so completed progress can be retained.

Responses increment the incoming revision once. The browser permits one current request, checks its request token and expected revision, and commits the response atomically before requesting another. Retrying identical inputs yields identical results. This is ordered single-client execution, not a server-authoritative shared session. Full snapshots are retained because the map is small.

The scheduler currently serves one drone. Multiple controllers will need action reservation, conflict resolution, fairness, and one world advance after the combined tick; calling today's single-drone action method once per drone would incorrectly accelerate the world. That work belongs to Stage 4.
