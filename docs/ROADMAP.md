# Roadmap — from a farm to a programmable factory

**Updated:** 2026-09-13. **Playable today:** Home farm, the Breadworks production chapter, and configurable crop care in both. Future stages below are proposals, not delivery commitments.

## Direction

Sprout is growing toward a Factorio-inspired automation game where Python controls useful decisions: how to supply machines, move products, diagnose stalled production, and improve throughput. Keep the agricultural identity and introduce systems in playable chapters.

The initial inspiration was Factorio's emphasis on factories, infrastructure, research, and transport bottlenecks. Sprout implements its own smaller farm-and-bakery loop. Sources: [Factorio overview](https://www.factorio.com/), [official belt transport guide](https://wiki.factorio.com/Belt_transport_system).

## Delivered milestones

| Stage | Implemented | Evidence / limits |
| --- | --- | --- |
| Home farm | Python drone, three crops, four missions, upgrades, editor, playback, local saves. | Original campaign and examples remain covered by tests. |
| 1 — Save foundation | Portable JSON saves, legacy migration, import validation and backup, CI configuration for Python 3.10–3.14 and JS syntax. | Published as `c42bfbe`. Local tests passed; remote CI execution is separately observable. Embedded-browser download completion was not confirmed. |
| 2 — First production chain | Separate Breadworks scenario, cargo, chest, mill, oven, depot, recipes, obstacles and routes, live machine status, six missions, three upgrades, four examples, optional timed delivery orders. | A finite script processes harvested wheat into delivered bread with conserved items. Saves preserve both chapters and active batches. One drone, fixed buildings, no conveyors or construction yet. |
| 2a — Crop care | Independent fertilizer, irrigation, and soil-health options; placeable sprinklers, supply management, compost, two shared scripts, and three extra goals. | All eight option combinations tested in both chapters. Existing saves migrate with options off. [Full rules](CROP_CARE.md). |

```mermaid
flowchart LR
    A[Wheat field] -->|Harvest 3 wheat| B[Drone cargo]
    B -->|Store or supply| C[Chest]
    C -->|Drone transport| D[Mill: 2 wheat → flour]
    D -->|Drone transport| E[Oven: flour → bread]
    E -->|Drone transport| F[Depot: 8 coins per bread]
    F --> G[Upgrades and delivery goals]
```

The current Python commands are documented in [PLAYER_GUIDE.md](PLAYER_GUIDE.md). A runnable supply fragment, assuming enough wheat and space:

```python
if stored("chest", "wheat") >= 4:
    if free_space("mill", "wheat") >= 4 and cargo_space() >= 4:
        navigate_to("chest")
        load("wheat", 4)
        navigate_to("mill")
        unload("wheat", 4)
```

The game now poses several distinct problems: a full drone cannot harvest; a full output stops a machine; missing input stalls production; rocks make direct routes impossible; a delivery order consumes an action budget; and faster machines can expose a transport bottleneck. Gather feedback on this loop before expanding the resource catalog.

## Proposed next milestones

| Stage | Deliverable | Completion check |
| --- | --- | --- |
| 3 — Continuous operation | Resumable interpreter, shared world scheduler, per-tick instruction quotas, pause/step/checkpoints, ordered state updates. | Long-running factories stay responsive; deterministic replays match; Stop/Pause act at a documented simulation boundary. |
| 4 — Logistics and building | A second drone, movement conflicts, placeable machines, limited-capacity conveyors, saved routes. | Controllers cooperate without duplicate items, permanent starvation, or double-speed world time. Blueprints preserve validated layouts. |
| 5 — Deeper production | Power, research, additional byproduct recipes, multiple recipes, varied contracts, throughput and idle-time graphs. | Players can see a bottleneck, change code, and measure improved output. |
| 6 — Scale and sharing | Larger maps, script/blueprint sharing, performance profiling, then optional accounts and hosting. | Representative worlds meet performance budgets; public execution has an isolated deployment design. |

These are independent milestones requiring scope decisions, rather than a promise to implement everything in sequence immediately. Completed authorized milestones are verified, documented, committed, and pushed before the next begins.

## Continuous simulation design

The present game simulates a whole bounded run and returns full state snapshots for browser playback. That is sufficient for the fixed one-drone Breadworks. Several persistent controllers need a different execution boundary:

1. Read the world at the start of the tick.
2. Resume each controller with a bounded instruction quota until it yields an action, finishes, or faults.
3. Resolve movement and transfers in a documented deterministic order. Reserve shared items so two drones cannot take the last item.
4. Advance crops, machines, and transport **once**. Define whether new outputs can move this tick or next; avoid accidentally traversing an entire belt in one tick.
5. Record events, controller frames, a new world revision, and an ordered update batch.

Use deterministic rotating priority for contested actions. Pause freezes the shared clock. Presentation speed changes animation only. Infinite computation loops must suspend or fault without freezing the game.

Do not remove the 400-action limit or create unrestricted host-Python threads to simulate continuity. First build explicit resumable execution frames and per-tick budgets. Preserve the named-call API and the ban on arbitrary attributes/imports unless a narrowly scoped language extension is designed and tested.

Session revision numbers should reject stale mutations. Checkpoint world state and controller position together. Ordered deltas with periodic snapshots can replace full frames after profiling; no framework rewrite is needed merely to add these mechanics.

## Save compatibility

The version 2 portable envelope already holds independent chapter saves. Classic worlds remain version 1; Breadworks worlds use version 2 with an explicit scenario, inventories, machine progress, upgrades, and order state. Legacy single-farm envelopes migrate into classic mode.

Future schemas must explicitly migrate existing chapters, including ingredients already consumed by active batches. Continuous controllers need versioned execution frames and safe reload/stop behavior. Add migration fixtures before changing storage and retain a recoverable backup.

Classic harvests sell immediately and classic scripts assume wrapped edges. Keep those semantics scoped to Home farm. Factory APIs and map rules must never silently reinterpret classic saves or tutorials.

## Later chains to explore

| Input | Possible chain | Programming challenge |
| --- | --- | --- |
| Sunflowers | Seeds → oil press → cooking oil | Share transport capacity with wheat. |
| Crop residue | Industrial compost → fertilizer production | Extend the existing simple compost mechanic into a machine production chain. |
| Carrots | Washing → packing → delivery | Balance two lines supplying the same depot. |
| Biomass | Fuel → generator → machine power | Prioritize machines when energy is scarce. |

Other useful work: collect balancing feedback, improve editor diagnostics, add automated browser regression coverage, test more browsers and text zoom, and audit keyboard/screen-reader interactions. Public hosting requires a production server and isolated execution; GitHub Pages cannot run the existing Python API.

## Growing-system direction

Following the owner's reference to [The Farmer Was Replaced](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/), Sprout now lets players opt into deeper resource and maintenance loops. The store's stated emphasis on gradual programming progression and resource-funded technology informs this direction. Fertilizer, irrigation, and soil care are implemented in Sprout with its own rules, rather than inferred as exact mechanics of the reference.

Future configurable modules could add weather, pests, crop rotation bonuses, and diseases. Each would need an explicit off-state behavior, bounded automation API, visible diagnosis, migration, and runnable example. None of those additional modules is included in the present crop-care release.
