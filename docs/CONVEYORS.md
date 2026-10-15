# Conveyor workshop

Implemented 2026-10-14. Bakery conveyors automate bounded item transport while Python controls crop care, inventory policy and feed gates. They are optional in the Breadworks campaign. Home farm and fixed challenges retain their rules.

## First conveyor bakery

1. Stop your program and finish any active delivery order.
2. Open **Conveyor workshop** below Workshop layout. Click **Auto-connect bakery** to preview three lane routes, then **Apply routes**. Building takes no coins or ticks and preserves stock.
3. Load **Conveyor delivery**. With at least eight chest wheat, built routes and conveyors enabled, the finite demo switches feeds on and waits for four more deliveries. It stops after at most 200 waits. From default fresh Breadworks it delivers four loaves in **40 ticks**. It may process all available grain, leaving additional products in machines; this is not the same workload/code as Layout delivery test.
4. Load **Conveyor farmer** for Continuous operation. The drone grows and stores grain and handles enabled care/recycling. It feeds grain in bursts, checks chest stock before each wait, and closes the inlet at four reserved wheat. Flour/bread keep moving while the grain feed is off. The script uses both policy and infrastructure rather than repeated machine trips.

For manual-transfer tutorials such as First bread, pause conveyors first: their fixed quantities assume stock remains available until the drone loads it. `stored()` and cargo queries exclude conveyor queues. Query or inspect the belts separately. Keeping manual transfers possible allows players to mix both transport methods.

## Routes and queues

| Name | Source → destination | Transported item |
| --- | --- | --- |
| `grain` | Chest → mill | Wheat |
| `flour` | Mill → oven | Flour |
| `bread` | Oven → depot | Bread, sold for the depot's normal price |

Select a route, then draw adjacent pads from **S** to **D**. Click an earlier step to backtrack; Redraw selected returns to S. Auto-route suggests a deterministic shortest valid lane path. Discard route preview restores installed paths. Apply routes installs the full preview and enables transport. Remove selected removes that route after its queue is empty.

A path contains 2–32 distinct tile indices on the 8×8 map, including source and destination. Steps must touch along cardinal edges. Paths cannot pass through crops, rocks, unrelated buildings or uninstalled recycling pads. Machine layout overrides determine endpoints. Drones can fly across belts. Different routes may cross on independent tracks: they do not merge or share segment inventory. Reversing, branching, shared belt junctions and recycling belts are future scope.

Each source/intermediate pad is a one-item segment; the destination is not a segment. Thus capacity is path length minus one, at most 31 per route / 93 total. Item type is fixed by the route. Default capacities are 3 grain, 3 flour and 4 bread. A longer route increases transit delay and ties up more stock.

### One shared clock

After committed drone actions and crop care, conveyors advance **once, before machine processing**:

1. Deliver the last segment's old item if the destination accepts it. Mill/oven respect their 12-item input capacities. Depot arrivals update coins, crop-sale income and lifetime bread deliveries exactly once.
2. Work backward through segments, moving old items at most one pad into available space. A vacancy can propagate backward, but an item cannot traverse multiple segments in this tick.
3. Pick up at most one source item into the first free segment if its feed is on. A newly picked item stays there until a later tick.
4. Advance machines once; new flour/bread can be picked up on the next phase. Then resolve orders, recycling/challenges and mission rewards using the existing phase rules.

A fresh item needs `segment_count + 1` enabled ticks from pickup phase to arrival (pickup counts as its first tick). Adjacent machines still use a one-item queue and require two phases. Full inputs create backpressure, without discarding items or starting overfilled batches. Both drones share the phase; two commands never double belt speed. Queries, browser wall time and offline time do not move items. Automatic arrivals count toward deliveries, deadlines and mission rewards; they are not additional drone commands or manual transfers in efficiency counters.

## Feed off, pause and safe rebuilding

- **Feed off** stops new pickups while queued items continue toward the destination. Per-route feed checkboxes update between programs. **Stop feeds and drain** turns every installed inlet off and enables the belt phase; run actions or waits until all queues reach zero.
- **Enable conveyors off** freezes every queue while crops/machines may continue. Paths, switches, items and counters are retained. Re-enable to continue.
- Removing or changing a path with queued items fails atomically. Drain first. An unchanged path retains slots and counters while switches change. Empty rerouted/new paths start fresh pickup/arrival counters.
- Even an empty connected route anchors its machines. Drain and remove routes before relocating their endpoint machines or placing another machine onto a belt. The layout preview and backend both enforce this rule.
- Active delivery orders block workshop configuration, including pause/rebuild. Python feed actions remain available during orders, making supply scheduling part of play. Challenges reject conveyor extensions even if empty or disabled.
- If a drain is blocked, inspect downstream input/output and keep flour/bread feeds on or move finished products with a drone. Turning every feed off can leave an upstream queue blocked by pre-existing full machines; paused queues never drain.

## Implemented Python API

Optional [stock targets](STOCK_TARGETS.md) now add `set_conveyor_policy`, `clear_conveyor_policy`, `conveyor_reserve` and `conveyor_target`. Feed-on is permission to pick up, while the policy may still hold intake. Targets count input, active ingredients and transit; lowering them keeps all existing stock. The new `reserve_held` / `target_met` statuses explain empty-queue holds. Legacy unpoliced routes keep the rules below.

| Call | Effect |
| --- | --- |
| `set_conveyor_feed("grain", True)` | Remote gate action from any drone pad. Requires a built route and strict boolean. Costs one shared tick; turning off prevents that phase's pickup. |
| `conveyor_items("flour")` | Number of queued items, zero for an unbuilt route. No tick. |
| `conveyor_status("bread")` | `not_installed`, `paused`, `blocked`, `moving`, `drained`, `ready`, or `waiting_input`. No tick. |

The three names above are the entire namespace. Status precedence is unbuilt, module paused, full destination with a last-slot item, any queued item, empty/feed-off, ready stock, missing source stock. A remote gate action uses a shared gate resource rather than the drone's physical tile. Two simultaneous changes to one gate alternate priority and retry; different gates can change together. Existing interpreter quotas and import/attribute restrictions apply unchanged. The new names are reserved builtins.

```python
# Drain grain while flour and bread continue.
set_conveyor_feed("grain", False)
while conveyor_items("grain") > 0:
    wait()
print(conveyor_status("grain"))
```

Observe stock before each action when enforcing a threshold: a gate left on during a long navigation or farming loop keeps consuming. Conveyor farmer demonstrates a burst loop rather than assuming a single stock check guarantees a permanent reserve.

## Save and HTTP contract

The optional factory extension is absent from untouched saves, preserving existing solo/team checkpoint hashes:

```json
"conveyors": {
  "version": 1,
  "enabled": true,
  "routes": {
    "grain": {
      "path": [48, 49, 50, 51],
      "feeding": true,
      "slots": [1, 0, 0],
      "picked": 1,
      "delivered": 0
    }
  }
}
```

Validation requires exact keys, strict booleans/integers, connected paths matching current station positions, one 0/1 slot per segment and bounded counters. Each route must satisfy **picked − delivered = sum(slots)**; conveyor bread arrivals cannot exceed lifetime deliveries. Route counters describe the current installation, not lifetime factory production. Invalid present extensions fail rather than silently dropping items. Save-envelope version 2 remains; portable solo/team continuations preserve exact paths, queues and gates and restore paused.

`POST /api/conveyors` takes `{state, enabled, routes}` where routes is the complete sparse replacement map `{name: {path, feeding}}`, excluding slots/counters. The server copies/validates state, validates all planned routes, rejects any loss of live queue stock, then returns `{state, message}`. Unchanged paths preserve inventory/ledgers. The endpoint keeps the 100,000-byte limit and loopback/Host/Origin protections. There is no persistent server world. Browser request tokens ignore stale replies. Configuring an untouched world off with no routes preserves its absent extension; installed empty/paused extensions remain for checkpoint identity.

## Verification and future scope

Tests cover hop latency, throughput, new-output timing, material conservation in every demo frame, full inputs and recovery, pause/drain, atomic rerouting/removal, machine-layout compatibility, old/new portable controllers, deterministic retries, gate contention, final-tick order success, schema bounds, endpoints and all sixteen care/recycling farmer variants. Node checks cover editor paths, reserved pads, custom layouts and relocation guards. Browser QA covers keyboard drawing, queues across reload, pause/drain/remove, demos, guides and responsive rendering.

Source reserves and committed-work targets are now implemented in [STOCK_TARGETS.md](STOCK_TARGETS.md). Construction costs, additional machines, programmable splitters, recycling routes, power and infrastructure-specific challenges remain independent proposals in [ROADMAP.md](ROADMAP.md).
