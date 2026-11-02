# Bread dispatch and storage branch

Implemented 2026-11-03. The optional oven→chest conveyor lets programs choose between earning coins now and keeping bread for later drone deliveries. This is one shared oven dispatcher with two independent tracks, not a generic belt-junction system.

## Start playing

1. Stop your campaign program and finish any active delivery order.
2. In **Conveyor workshop**, use Auto-connect bakery and Apply routes for the original three tracks.
3. Select **Bread storage: oven → chest**, use Auto-route or draw an adjacent lane path, and Apply routes. Both Bread delivery and Bread storage are required. Building costs no coins or ticks. First installation selects **Sell**, preserving the original bakery flow.
4. Choose Bread dispatch: Sell, Store or Balanced. Stock already queued keeps its destination. Route cards, arrows, shared chest contents and Intake text show what is happening.
5. Load **Bread branch demo** from a fresh bakery with 12 chest wheat, no chest bread, empty machine buffers/batches and queues, and four free chest slots. It stores four loaves, switches to selling, then sells two. Default layout completes in **52 ticks**. It performs at most 320 waits plus setup actions, within Bounded run limits.
6. Load **Balanced bakery** for Continuous farming with optional care/recycling. Its policies keep four wheat and four bread in the chest while selling further output. Reload/import restore paused.

Stored bread is not a sale and does not count toward delivery missions or orders. Use normal drone `load("bread", n)` at the chest and `unload("bread", n)` at the depot to release a stockpile. The chest's 48 slots are shared by all item types; storing too much bread can interfere with grain storage.

## Dispatch rules

| Mode | New oven pickups |
| --- | --- |
| `sell` | Only Bread delivery may take a loaf. No fallback to storage. |
| `store` | Only Bread storage may take a loaf. No fallback to selling. |
| `balanced` | Alternate preferred branches after successful pickups. If the preferred branch cannot take a loaf, try the other eligible branch. |

The two branches share **at most one new oven loaf per world tick**, regardless of drone count. The persisted next preference starts with sale. No pickup means no turn change. Forced modes retain the balanced preference for a later return to Balanced. Eligibility respects the module pause, route feed, first-segment space, source reserve and destination target. Backpressure eventually fills blocked queues; a blocked final destination can still allow pickups into earlier free segments until those fill too.

Conveyor phases deliver and move old items on all tracks, then pick up new items. Each old item advances at most one segment. Machine processing follows; freshly baked loaves wait for the next phase. Changing dispatch affects future pickups only: a sale-bound loaf may arrive after switching to Store, and a storage-bound loaf may arrive after switching to Sell. There is no teleportation, lost inventory or retroactive rerouting.

Bread storage uses the same 2–32-pad validation as other tracks: no crops, rocks, unrelated buildings or repeated pads. Its default route has eight segments. Crossings remain independent tracks. A full chest blocks its arrival; stock is retained. Removing/rerouting live tracks fails atomically. Drain storage before removing it; the sale track cannot be removed while storage remains installed. Existing machine-layout guards apply.

## Stock policies

The new route name is **`bread_store`**. Existing queries, feeds and policies support it:

```python
set_conveyor_policy("bread_store", 0, 4)
set_conveyor_feed("bread_store", True)
set_bread_routing("balanced")
```

Its reserve is 0–8 completed oven bread. Its destination target is 0–48 **chest bread + storage-route transit**, or `None` for unlimited. Other chest items do not count toward the bread target, but occupy shared capacity and may cause a full-chest block. Lowering targets retains every item. Balanced stock targets applies a storage goal of four when that branch is installed; the original three route presets retain their values.

Reserves belong to each intake, not the whole oven: if sale holds one loaf but storage reserves zero, Balanced may send that loaf to storage. Use matching reserves on both branches if you want the oven itself to retain output. Feed off still drains queued material; module pause freezes it. `routing_hold` explains a feed-on branch excluded by a forced dispatch mode. Moving/blocked/paused status precedence remains, while Intake shows the hold separately.

## Implemented Python and HTTP API

- `set_bread_routing("sell" | "store" | "balanced")` is a remote one-tick action from any drone pad. It requires both installed branches and applies before that tick's pickup decision. Invalid values fail without advancing or changing world state.
- `bread_routing()` is a zero-tick query returning the saved mode, or `not_installed` before storage is built. Names are reserved builtins; existing language limits apply.
- Two drones changing dispatch share a single rotating reservation. A losing command retries with fresh observations. A dispatch change and a per-route feed/policy change can both commit in a tick; both affect the single transport phase. No source item is duplicated.
- Runtime dispatch actions remain available during campaign orders. Workshop changes remain blocked during an active order. Fixed challenges reject configuration and retain their original snapshots and records.
- `POST /api/conveyor/routing` takes `{state, mode}` and returns `{state, message}` without charging time/coins or changing inventory. It uses copied-world validation, normal 100,000-byte limits, loopback/Host/Origin protection and browser request tokens.

## Saves and compatibility

The original conveyor version and save-envelope version remain unchanged. Old three-route worlds retain their exact schema/digests. When storage is installed, conveyors also save:

```json
"routing": {"version": 1, "mode": "balanced", "next": "bread_store"}
```

Validation requires both branches and this exact routing record. Malformed, missing or orphaned records fail rather than silently choosing a destination. Pause, feed changes and valid empty reroutes preserve mode/preference. Removing the empty storage route removes its dispatcher; the remaining three-route schema can match its legacy form again.

Each track retains its pickup−arrival=queued ledger. Storage arrivals increase chest bread, not sold-bread counters. Portable solo/team checkpoints retain paths, queues, policies, mode and next preference and restore paused. Existing checkpoints without storage remain valid. Layout and phase rules are unchanged for existing three-route games.

## Verification and future scope

Tests cover shared-source throughput and alternation, forced holds, full/target-held fallback, conserved queued destinations during mode switches, chest capacity and refill after drone loads, policy/layout bounds, pause/removal safety, old/new continuations, next-turn restoration, deterministic retries, team dispatch conflicts, order/trial restrictions, HTTP validation and both example layouts. Balanced bakery sustains all sixteen care/recycling combinations over 650 ticks each, keeping four wheat and at most four committed chest bread.

General-purpose junctions, configurable branch ratios, recycling branches, extra buildings, power and branch-specific scored scenarios remain proposals. The implemented choice is explicitly sale versus bread storage from one oven.
