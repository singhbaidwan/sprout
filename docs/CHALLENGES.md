# Automation challenges and efficiency — implemented

Delivered 2026-10-03. Available in **The Breadworks**, independently of campaign missions and delivery orders. These are Sprout's original scenarios; records are personal, editable local-save data.

## Play and improve

1. Open Breadworks and stop any current program.
2. Choose **Bakery Rush**, **Waterwise Harvest**, or **Full Buffers**, and one or two drones. Press **Start challenge**.
3. Run the supplied program, or write your own. Two drones use separate farmer/courier programs; solo uses a combined routine. Challenges start in Continuous or Drone team mode.
4. Inspect the efficiency dashboard. Stop to edit, then **Retry with my code** for the same starting farm. Retry preserves both scripts, speed, and execution mode; it clears the world and checkpoint. Use Continuous for Waterwise: its 500-tick budget exceeds the bounded runner's 400-action cap.
5. Success or an exceeded budget stops automatically. Compare the result with your best and previous resolved attempt. **Return to farm** restores your campaign world, programs and speed. **View saved attempt** reopens a parked trial; reload/import restore any controller paused.

One trial is retained. Starting another replaces that trial; campaign chapters and personal records remain. An abandoned or stopped program does not count as a resolved attempt. A program error leaves the attempt active so you can repair it without restarting, but the clock already spent remains. No actions run while paused or while the page is closed.

## Fixed rules, version 1

All scenarios use the normal 8×8 Breadworks map, four fixed buildings, standard recipe timings, 8-slot cargo, no upgrades, 30 starting coins, and zero lifetime stats. Fertilizer and soil health are off. The tank starts at 60 and the pump is off. Drones start at (0,0); Drone 2, if selected, starts at the chest (0,6). Machine batches are initially idle except for the stocked buffers below. Unspecified supplies/tiles use the normal new Breadworks state.

| Scenario | Starting production / field | Goal | Shared tick budget | Tank-water budget |
| --- | --- | --- | --- | --- |
| Bakery Rush | Chest: 24 wheat; four ripe wheat plots; empty machines | Deliver at least 12 bread | 180 | None; irrigation off |
| Waterwise Harvest | Empty chest/machines; six dry, newly planted wheat plots on row 0 | Deliver at least 12 bread | 500 | At most 24; irrigation on |
| Full Buffers | Chest: 48 wheat; mill: 12 input + 8 output; oven: 12 input + 8 output; four ripe wheat plots | Deliver at least 24 bread | 240 | None; irrigation off |

Growing settings, drone count, upgrades and building layout stay fixed within an attempt. The server rejects settings changes, upgrades, ordinary orders, measurement resets, and execution modes with the wrong drone count. Ordinary Python crop/transport commands remain available. Waterwise permits sprinkler installation, pump control and refills, but every tank unit consumed still counts. Manual watering costs 2; each sprinkler pulse costs 1. Refilling increases available supply and does not erase consumption. With irrigation off, manual watering consumes no tank units; a zero score is not an estimate of agricultural water use.

After the tick's actions, the world advances once, then resolves the contract: exceeding the water budget fails first; meeting the delivery target succeeds, including on the exact deadline; otherwise reaching the deadline fails. An entire valid transfer can exceed the delivery target. Both drones finish their actions in that shared tick. Terminal attempts cannot advance further. Bounded and resumable execution stop cleanly when the contract resolves, including inside an infinite loop or route.

### Starter results from local simulation

These are working baselines, not optimal solutions. Changing the starters/rules can change these numbers.

| Scenario | 1 drone: ticks / water / empty moves | 2 drones: ticks / water / empty moves |
| --- | --- | --- |
| Bakery Rush | 143 / 0 / 84 | 149 / 0 / 113 |
| Waterwise Harvest | 462 / 24 / 239 | 219 / 24 / 223 |
| Full Buffers | 117 / 0 / 60 | 111 / 0 / 69 |

A second drone is useful when its role addresses the current constraint. Extra field work need not improve a stocked-grain rush. Try specializing transport, collecting products before outputs fill, or watering only actively growing crops.

## Efficiency measurements

The dashboard is also available in the normal Breadworks campaign. Its first successful action starts a measurement window. **Restart measurement** between programs begins at the current tick and delivered count without changing the farm or advancing time. Historical stats are not reconstructed. Challenges measure their entire attempt from tick zero and cannot reset the window.

- **Loaves / 100 ticks:** deliveries since the baseline × 100 / shared ticks. Displays a dash before time advances.
- **Tank water / loaf:** all manual and automatic tank consumption in the window / delivered loaves. Displays a dash before any delivery. Changing campaign care settings does not clear the window.
- **Empty travel:** moves begun with zero items in that acting drone's cargo / all measured moves. A partially loaded drone counts as loaded. Navigation counts each tile movement.
- **Waits / transfers:** successful `wait()` commands and successful `load()`/`unload()` commands, rather than transferred item counts. Contested or failed actions do not count as successful commands.
- **Machine time:** each machine receives exactly one category per shared tick, after transfers. Working includes starting, running and completing a batch. Output full means it cannot start because its product buffer is full. Otherwise it is waiting for input. Categories sum to 100% before display rounding; the text percentages can differ by one point after rounding.

Two drones can execute two successful commands per world tick; machines, crop growth and sprinklers still advance once. The hint reports the largest accumulated machine waiting category. It is a diagnostic starting point, not proof that fixing it alone yields optimal throughput. Measurement counters are window totals; time-series graphs and player-visible metric Python sensors are not implemented.

## Personal records and save compatibility

Six record groups separate scenario and drone count (`rush:1`, `rush:2`, etc.). Successful records rank by lower ticks, then lower water, then lower empty moves. Each group retains the best success, last resolved result, previous resolved result, and count of resolved attempts. Failed attempts never replace a successful best. Comparing consecutive successes shows changes in ticks, water and empty moves. Reloading an already recorded result does not increment the count again.

The existing version 2 portable envelope retains campaign saves in `games`. Optional `trial = {active, recorded, game}` holds the separate validated factory state, scripts, mode, speed and checkpoint; `challenge_records` holds bounded scores. `active: true` requires the factory chapter to be selected and a saved factory campaign. The `recorded` marker lives outside the checkpoint-bound world. Export/import includes campaigns, the trial and records. Records are not authenticated or an online leaderboard.

Breadworks worlds gain optional `efficiency.version = 1` and trial worlds additionally carry `challenge = {version: 1, id, drones, status}`. Missing metrics are preserved during validation, so old world/checkpoint hashes stay valid. Metrics attach on the next successful action or an explicit campaign measurement reset. Existing team/solo checkpoint formats and the classic chapter are unchanged. Malformed metric versions, counters, clock/category totals, trial rules, terminal checkpoints or records are rejected.

Implemented HTTP endpoints:

| Endpoint | Request | Result |
| --- | --- | --- |
| `POST /api/challenge/start` | `{id, drones: 1 or 2}` | Fixed `state` and two `codes`; solo uses the first |
| `POST /api/efficiency/reset` | `{state}` | Campaign state with a fresh window and a message |

Bootstrap includes the challenge catalog. Save validation now permits up to 1,000,000 request bytes; browser imports permit files up to 990 KB. Controller/team requests retain their 600,000-byte limit, other requests 100,000. The interpreter allowlist, operation/memory quotas and loopback hosting boundary remain unchanged. Future rule changes need an explicit scenario-version/record migration; do not mix scores from different definitions.

Optional campaign recycling is excluded from all version 1 trial worlds, including its disabled extension. The configuration endpoint rejects changes during trials, so the six starter baselines and comparable records retain their original item catalog and clock. Campaign measurements include all cargo when counting empty moves and transfers; mill/oven utilization graphs still describe bakery machines only. [Campaign recycling rules](RECYCLING.md).
