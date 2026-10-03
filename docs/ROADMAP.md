# Roadmap — from a farm to a programmable factory

**Updated:** 2026-10-03. **Playable today:** Home farm, the Breadworks production chapter, configurable crop care, continuous automation, two-drone Breadworks teams, three measured automation challenges, and an optional residue → compost → fertilizer chain. Future stages below are proposals, not delivery commitments.

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
| 3 — Continuous operation | Optional resumable Python execution, one-action shared-clock boundary, bounded work, ordered browser updates, portable checkpoints, and two continuous examples. | One drone; reload/import restore paused. Deterministic retry and checkpoint tests pass, including all care combinations. [Rules and limitations](CONTINUOUS.md). |
| 4 — Two-drone teams | Separate Python controllers and cargo; deterministic shared work; one clock; portable team checkpoints. | All care combinations sustain production. [Rules](DRONE_TEAMS.md). |
| 4a — Efficiency and challenges | Shared-clock dashboard; Bakery Rush, Waterwise Harvest, Full Buffers; one/two-drone records; isolated trial saves and retry. | All six starters complete under fixed budgets. Old checkpoint hashes remain valid; campaign restores independently. [Rules](CHALLENGES.md). |
| 4b — Crop recycling | Optional harvest residue, composter, fertilizer mixer, six-item cargo/chest, live stock and return goals, two examples. | Conserved materials, one shared phase, pause/resume, old checkpoint compatibility and all care combinations tested. [Rules](RECYCLING.md). |

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
| 4 — Logistics and building | Two-drone teams and efficiency scenarios delivered; next consider placeable machines, limited-capacity conveyors and saved routes. Physical movement conflicts are optional future scope. | Controllers cooperate without duplicate items, permanent starvation, or double-speed world time. Blueprints preserve validated layouts. |
| 5 — Deeper production | Residue/compost/fertilizer delivered; later consider power, research, additional recipes, varied contracts and broader utilization graphs. | Players can see a bottleneck, change code, and measure improved output. |
| 6 — Scale and sharing | Larger maps, script/blueprint sharing, performance profiling, then optional accounts and hosting. | Representative worlds meet performance budgets; public execution has an isolated deployment design. |

These are independent milestones requiring scope decisions, rather than a promise to implement everything in sequence immediately. Completed authorized milestones are verified, documented, committed, and pushed before the next begins.

## Multi-controller simulation design — implemented for two drones

The present game supports bounded playback, resumable solo control, and an optional two-drone Breadworks team. The team extends the original one-action clock as follows:

1. Read the world at the start of the tick.
2. Resume each controller with a bounded instruction quota until it yields an action, finishes, or faults.
3. Resolve actions in alternating drone priority. Reserve shared work pads and apply transfers atomically so two drones cannot take the last item. Drones fly in separate air lanes and may cross paths.
4. Advance crops, machines, and transport **once**. Define whether new outputs can move this tick or next; avoid accidentally traversing an entire belt in one tick.
5. Record events, controller frames, a new world revision, and an ordered update batch.

Use deterministic rotating priority for contested actions. Pause freezes the shared clock. Presentation speed changes animation only. Infinite computation loops must suspend or fault without freezing the game.

Keep the existing 400-action bounded mode and the explicit continuous execution frames with per-step budgets. Do not introduce unrestricted host-Python threads. Preserve the named-call API and the ban on arbitrary attributes/imports unless a narrowly scoped language extension is designed and tested.

The current browser checks request tokens and checkpoint revisions, and checkpoints world and controller together. The team binds both sources and world in one checkpoint. A future shared server session must also reject stale mutations authoritatively. Ordered deltas with periodic snapshots can replace full frames after profiling; no framework rewrite is needed merely to add these mechanics.

## Save compatibility

The version 2 portable envelope already holds independent chapter saves. Classic worlds remain version 1; Breadworks worlds use version 2 with an explicit scenario, inventories, machine progress, upgrades, and order state. Legacy single-farm envelopes migrate into classic mode.

The optional recycling extension preserves old item maps/checkpoints until enabled, retains paused batches and validates a conserved-material ledger; see [RECYCLING.md](RECYCLING.md). The optional team extension preserves old saves and checkpoints; see [DRONE_TEAMS.md](DRONE_TEAMS.md). The optional efficiency/trial/record extensions preserve campaigns and old checkpoints; see [CHALLENGES.md](CHALLENGES.md). Future schemas must explicitly migrate existing chapters, including ingredients already consumed by active batches. Continuous controllers now have versioned execution frames and paused reload behavior; old saves default to finite mode. Add migration fixtures before changing storage and retain a recoverable backup.

Classic harvests sell immediately and classic scripts assume wrapped edges. Keep those semantics scoped to Home farm. Factory APIs and map rules must never silently reinterpret classic saves or tutorials.

## Later chains to explore

| Input | Possible chain | Programming challenge |
| --- | --- | --- |
| Sunflowers | Seeds → oil press → cooking oil | Share transport capacity with wheat. |
| Crop residue — delivered | Residue → compost → fertilizer production | Split composter output between soil care and fertilizer. Additional fuel recipes remain proposed. |
| Carrots | Washing → packing → delivery | Balance two lines supplying the same depot. |
| Biomass | Fuel → generator → machine power | Prioritize machines when energy is scarce. |

Other useful work: collect balancing feedback, improve editor diagnostics, add automated browser regression coverage, test more browsers and text zoom, and audit keyboard/screen-reader interactions. Public hosting requires a production server and isolated execution; GitHub Pages cannot run the existing Python API.

## Growing-system direction

Following the owner's reference to [The Farmer Was Replaced](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/), Sprout now lets players opt into deeper resource and maintenance loops. The store's stated emphasis on gradual programming progression and resource-funded technology informs this direction. Fertilizer, irrigation, and soil care are implemented in Sprout with its own rules, rather than inferred as exact mechanics of the reference.

Future configurable modules could add weather, pests, crop rotation bonuses, and diseases. Each would need an explicit off-state behavior, bounded automation API, visible diagnosis, migration, and runnable example. None of those additional modules is included in the present crop-care release.


## Current design recommendation

The two-drone team is implemented. Factorio / The Farmer Was Replaced research and a ranked proposal list are in [DESIGN_DIRECTION.md](DESIGN_DIRECTION.md). The efficiency dashboard and three reproducible contract scenarios are delivered; see [CHALLENGES.md](CHALLENGES.md). The conserved residue → compost → fertilizer chain is delivered; see [RECYCLING.md](RECYCLING.md). The next proposed bounded milestone is player-controlled logistics, starting with validated machine placement or short conveyor segments. Those systems need a scope decision and are not shipped APIs.
