# Programmable stock targets

Implemented 2026-10-16. Optional policies on existing bakery conveyors keep a source reserve and limit work committed to a destination. This gives players an inventory-control problem while retaining the same bounded transport and shared world clock. The optional bread_store route now supports an oven reserve and a 0–48 chest-bread-plus-transit target; see [BREAD_ROUTING.md](BREAD_ROUTING.md).

## Play

1. Build and enable the three routes in **Conveyor workshop**. Stop your program; finish an active order before workshop changes.
2. Choose a route using **Plan route**. In **Stock targets**, set a Source reserve and optional Destination target, then Apply stock policy. Configuration takes no time or coins and keeps all stock, batches and both drones.
3. **Balanced stock targets** applies grain reserve 4 / target 6, flour reserve 0 / target 3, and bread reserve 1 / no target to installed routes. The bread reserve intentionally holds one loaf at the oven: lower it to zero when you want to sell every loaf.
4. Inspect cards and **Intake** feedback. Reserved stock or a satisfied target can hold intake while items already on the route continue moving. Clear selected policy restores ordinary manual-feed behavior without changing the feed switch.
5. Load **Stock target demo** with at least 12 chest wheat. It sets grain 4/6, flour 0/3 and bread 0/unlimited, switches feeds on, and delivers four loaves. Fresh default Breadworks completes in **40 ticks**, leaving four chest wheat. It has a finite 240-wait bound.
6. Load **Target-managed farmer** for Continuous operation with optional care/recycling. Its program sets policies once and grows grain while the belts enforce limits every tick. Reload/import restore its controller paused as usual.

Apply or discard a pending route preview before changing policies. Invalid values explain their bounds. Bread has no destination target because the depot sells arrivals immediately. Machine targets below one ingredient batch can stall production; the form explains this rather than silently changing the player's choice.

## Rules

| Route | Source reserve | Destination target |
| --- | --- | --- |
| Grain | 0–48 wheat in chest | 0–12 wheat committed to mill, or unlimited |
| Flour | 0–8 completed flour at mill | 0–12 flour committed to oven, or unlimited |
| Bread | 0–8 completed bread at oven | Always unlimited (`None`) |

All values are strict integers; booleans and fractions fail. An empty target field maps to `None`. Zero prevents new pickups, while existing queues continue to drain. A reserve equal to the source's maximum capacity prevents all pickups. Source reserves are available to drones: policies constrain conveyor pickups, not manual transfers.

For grain/flour, committed work is **destination input + ingredients reserved by its active batch + all items in that route's transit slots**. An active mill batch reserves two wheat; an oven batch one flour. Finished destination products are excluded. Counting transit prevents oversupply; counting active ingredients prevents refilling too early. Once a batch finishes, its committed ingredients leave the count and space can become available for another pickup.

Every existing conveyor phase still delivers the last old item, advances old items one hop, then considers one pickup. Policy checks use post-action source inventory and post-hop/arrival queues. A pickup is allowed only if the feed is on, source stock exceeds its reserve, and committed work is below the target. Targets are **soft intake limits**: lowering them does not destroy queued stock or ingredients; manual drone supplies may also put work above a target. No new pickups happen until the committed count falls below the new limit.

Manual feed off always stops intake, regardless of policy. Module pause freezes queues. Stop feeds and drain remains usable: drain old stock before removing or rerouting tracks. Policies cannot bypass route-layout validation, input capacities, item conservation or the once-per-shared-tick rule.

Overall `conveyor_status` retains unbuilt/paused/blocked/moving precedence. When no queue is moving and the feed is on, it may return `target_met` or `reserve_held`, in addition to `ready` and `waiting_input`. The separate Intake text explains these holds even when old queue items are moving. Feed off returns ordinary `drained` after emptying.

## Implemented Python API

```python
set_conveyor_policy("grain", 4, 6)
set_conveyor_policy("flour", 0, 3)
set_conveyor_policy("bread", 1, None)
print(conveyor_reserve("grain"), conveyor_target("grain"))
```

- `set_conveyor_policy(name, reserve, target)` is a remote one-tick action requiring a built route. `None` means unlimited; bread requires it. The policy applies to that action's transport phase.
- `clear_conveyor_policy(name)` is a remote one-tick action. It removes the optional policy, keeping manual feed state and existing material. If the feed is on, ordinary pickups may resume in that phase.
- `conveyor_reserve(name)` and `conveyor_target(name)` are zero-tick queries. They return `0` / `None` when a known route has no policy or is not installed. Unknown names fail.
- Names are `grain`, `flour`, `bread`, and optional `bread_store`. The four new builtin names are reserved; existing interpreter quotas/import/attribute limits remain unchanged.

Policies, clearing and manual feed changes share the same named gate resource. Two drones changing one route alternate priority and retry; different routes can be changed together. Belts still advance once after committed team actions. Python policy actions remain available during campaign orders, so players can release reserves for deliveries. Workshop configuration stays locked during active orders. Fixed trials retain their original rules and reject conveyor/policy configuration.

## Save and HTTP contract

A version 1 conveyor route may carry an optional policy:

```json
"policy": {"version": 1, "reserve": 4, "target": 6}
```

This field is absent in old worlds/routes, preserving old solo/team checkpoint digests. Present explicit defaults (`0`, `null`) survive validation because dropping them would change a continuation's world identity. Present malformed/null policies fail. Clearing deliberately removes the field; a previously created checkpoint must then be restarted. Normal UI changes require Stop first. Portable saves retain exact policy values, queues and batch state; no envelope or conveyor version bump is needed.

`POST /api/conveyor/policies` accepts `{state, policies}`. The bounded update map contains at most four route names, each with a policy object or `null` to clear. It preflights every built route and policy before changing any, returns `{state, message}`, and takes no simulation time. The server remains stateless, loopback-only, with 100,000-byte requests and Host/Origin protections. Existing browser request tokens reject stale responses. An empty update is a no-op.

`POST /api/conveyors` also accepts an optional policy in each planned route. Omitted policies preserve the previous logical route's policy through pause/feed changes or an empty reroute; explicit `null` clears it. Removing the route removes its policy. Live reroute/removal remains prohibited. A new route without a policy keeps legacy behavior.

## Verification and limits

Tests cover unpoliced legacy continuations, exact reserve/target checks, active ingredients and transit, lower-target stock preservation, zero/sub-batch stalls, bread reserves, post-drone inventory, strict/batch-atomic validation, policy-preserving rebuilds, team arbitration, HTTP limits/guards, portable continuations, deterministic retries, conserved demo frames and all sixteen care/recycling farmer combinations. Node checks mirror policy feedback/committed totals and value bounds. Browser QA covers apply/clear/preset, reload, paused queues, field validation and mobile/desktop controls.

These policies support the three core bakery flows and optional bread storage. Sale/storage dispatch is now implemented in [BREAD_ROUTING.md](BREAD_ROUTING.md). They do not add chest restocking robots, generic storage buildings, branch routing, splitters, research, extra machines or power. Those remain separate proposals in [ROADMAP.md](ROADMAP.md).
