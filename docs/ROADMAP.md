# Roadmap — from a farm to a programmable factory

**Date:** 2026-09-13. **Status:** design proposal, not implemented or a delivery commitment. The existing farm game remains the playable baseline.

## Recommendation

Yes: Sprout can grow into a Factorio-inspired automation game where programming is a central way to build and operate the world. Keep the agricultural identity: fields supply production lines, drones deliver items, and code coordinates the operation. The player should see their program create a working system and then diagnose why it is not producing enough.

Factorio's official description emphasizes factories, infrastructure, research, and automated production. Its belt documentation shows how transport capacity and bottlenecks become design problems. Those are useful points of inspiration for Sprout's own mechanics. This is a proposal for our game, not a claim that any of these systems already exist here. Sources: [Factorio overview](https://www.factorio.com/), [official belt transport guide](https://wiki.factorio.com/Belt_transport_system).

**Proposed player journey:** automate one field → store harvests → feed a machine → make a product → connect production stages → coordinate several drones → improve throughput under resource constraints.

## The first factory should make bread

```mermaid
flowchart LR
    A[Wheat field] -->|Harvest| B[Drone cargo]
    B -->|Unload| C[Storage]
    C -->|Supply wheat| D[Mill]
    D -->|Flour| E[Oven]
    E -->|Bread| F[Delivery depot]
    F -->|Order rewards| G[Research and expansion]
```

Start with one field, one drone, a storage chest, a mill, an oven, and a delivery depot. Direct drone transport is enough to prove the production loop. Conveyors can follow once inventory and processing rules work.

An early mission could be: **deliver 20 loaves within 300 simulation ticks, then improve the solution to use fewer drone actions**. The quantities and timing are initial design targets to balance through playtesting, not implemented game rules.

The challenge becomes meaningful when buffers fill, ingredients run short, and travel consumes time. A machine inspector should explain “waiting for wheat,” “output full,” or “processing: 3 ticks left.” Players need visible causes they can respond to in code.

Later agricultural chains could include:

| Input | Processing chain | New programming problem |
| --- | --- | --- |
| Sunflowers | Seeds → oil press → cooking oil | Share transport capacity with wheat. |
| Crop residue | Compost → fertilizer → better crop yield | Route byproducts and maintain a reserve. |
| Carrots | Washing → packing → delivery | Balance two lines feeding the same depot. |
| Biomass | Fuel → generator → machine power | Prioritize machines when power is scarce. |

## How programming would feel

Introduce capabilities gradually. The current farm commands teach loops and conditions; factory commands should add inventory checks, machine state, routes, and priorities. Basic movement and farming remain available.

An illustrative future routine, **not runnable in the current release**:

```python
# Factory-mode proposal. These new APIs do not exist yet.
def supply_mill():
    if stored("grain_chest", "wheat") >= 4:
        if free_space("mill", "input") >= 4:
            navigate_to("grain_chest")
            load("wheat", 4)
            navigate_to("mill")
            unload("wheat", 4)

for cycle in range(50):
    supply_mill()
    wait()
```

For the initial prototype, a small read-only query API with entity IDs keeps compatibility with the current named-call interpreter. A convenient object API such as `mill.inventory` would require an explicit, narrowly scoped language extension; arbitrary Python attributes should remain unavailable.

Queries can be free in simulation time but must still consume interpreter budget. A command such as `navigate_to` must resolve into visible per-tile actions with defined time costs. It must report unreachable destinations rather than teleporting or looping forever. Inventory transfers should define capacity, range, and failure behavior; checks are informative, while command execution must revalidate and perform the transfer atomically.

Avoid making the player repeatedly type setup code just to lay out identical machines. A later blueprint system can save a reviewed arrangement and its parameters. Code should decide useful policies, including when to deliver, how much stock to reserve, and which orders to prioritize.

## Code changes the current design needs

| Current implementation | Why it matters | Proposed change |
| --- | --- | --- |
| `Farm.action("harvest")` immediately credits coins. | Production chains need crops to exist as items. | Add typed item inventories and explicit selling/delivery in the factory scenario. Preserve classic farming behavior. |
| `Farm.advance()` runs after every drone action. | With several drones, calling it per drone would accelerate crops and machines. | A world scheduler advances one shared tick, resolves each drone's action, then advances world systems once. |
| `Interpreter.run()` executes a whole bounded script at once. | Multiple active controllers and interactive factories need programs that can pause and continue. | Introduce resumable interpreter state using explicit execution frames; retain bounded instruction work per tick. |
| Every action frame deep-copies the whole farm. | Larger worlds and transport items would create large responses and allocation costs. | Emit ordered state changes with sequence numbers and periodic full snapshots; profile before selecting a transport. |
| The browser owns the displayed save and posts it on every request. | Continuing a simulation across requests needs a clear ownership model. | Give each local game session a revision and checkpoint; reject stale mutation requests and define pause/save recovery. |
| Tiles combine soil and crops on a fixed 6/8 grid. | Machines and terrain require footprints and occupancy. | Add entities and building definitions separately from terrain; support obstacles and explicit pathfinding. |
| Crop and upgrade information spans Python, JavaScript, and guides. | New content can drift between engine rules and interface text. | Return validated content definitions from one authoritative catalog and render the workshop/reference from it. |

Keep the existing Python/backend and browser/canvas split. These mechanics do not require a framework rewrite. Establish stable interfaces between systems before adding more content.

### Deterministic scheduling

A proposed world tick:

1. Read the state at the start of the tick.
2. Resume each controller under an instruction quota until it yields an action, finishes, or faults.
3. Resolve movement and item requests using a documented deterministic order. Reserve shared resources so two drones cannot both take the last item.
4. Advance crop growth, machine recipes, and transport once. Define whether outputs become usable this tick or next; avoid multiple transfers across an entire belt in one tick by accidental iteration order.
5. Record events, updated entities, inventory totals, and the next revision.

For contested actions, use deterministic round-robin priority so one drone is not permanently starved. Pause freezes the shared clock. Presentation speed does not alter results. An infinite computation loop should fault or suspend its controller without freezing the farm or the browser.

Do **not** implement continuous factories by simply removing the existing 400-action limit or launching one uncontrolled host-Python thread per drone. The current limit protects a finite interpreter; continuous play needs a bounded, resumable execution model.

### Save compatibility

Add a separate factory scenario using the shared simulation components. Version 1 farm saves should continue to load in classic mode. Factory saves need explicit inventory, building, recipe-progress, controller, and scenario versions. Design and test migration before changing storage, and keep an exportable backup during upgrades.

In particular, classic missions count crop-sale income and the starter scripts assume immediate coin rewards. Changing `harvest()` globally would silently break both; the new scenario must specify its economy and tutorial separately.

## Prioritized work

| Stage | Deliverable | Completion check |
| --- | --- | --- |
| 1 — Foundation | Portable save export/import with schema migration tests; CI for supported Python versions and JS syntax; editor/readability improvements. | A saved farm round-trips without loss, malformed imports preserve the current save, and a clean checkout passes the test matrix. |
| 2 — First production chain | Factory scenario, cargo/chests, mill, oven, depot, recipes, and a delivery mission. Use finite programs and one drone initially. | A script turns harvested wheat into delivered bread with conserved items and visible machine status. Classic examples still pass. |
| 3 — Continuous operation | Shared world clock, resumable interpreter, per-tick instruction quotas, pause/step/checkpoint semantics, and ordered updates. | Long-running factories stay responsive, deterministic replays match, and Stop/Pause affect the documented simulation boundary. |
| 4 — Logistics | A second drone, movement conflicts, routes, and simple conveyors with limited capacity. | Two controllers cooperate without duplicating items, starving each other, or advancing the world twice per tick. |
| 5 — Deeper goals | Research, power, fertilizer/byproducts, production contracts, throughput and idle-time graphs. | Players can identify a bottleneck and improve measured output through program changes. |
| 6 — Scale and sharing | Larger maps, blueprint/script sharing, performance profiling, then optional hosted accounts. | Representative large-world benchmarks meet agreed budgets; hosted execution has a separate isolation design. |

The immediate development target should be **Stage 1 followed by the bread-chain prototype**. Validate that supplying and debugging one chain is enjoyable before adding dozens of machines or resources.

## Other improvements worth making

- **A more useful editor:** command completion, inline signatures, error-line navigation, reliable undo for indentation, saved scripts, and a variable inspector. A true source debugger needs interpreter work; current Step advances one drone action.
- **Maintainable frontend modules:** split `static/app.js` into editor, playback, persistence, and guide modules; format the compressed CSS into readable sections. Keep interfaces small and test pause/stop/save behavior when refactoring.
- **One definition of game content:** derive API help, crop prices, upgrade costs, and example metadata from versioned definitions instead of keeping copies synchronized manually.
- **Stronger regression coverage:** add browser tests for load → run → pause → step → stop → reload; add seedable scenario/replay tests and checks for item conservation when inventory arrives.
- **Clearer goals:** add a small campaign selection screen with finite automation puzzles, optional efficiency targets, and useful completion statistics.
- **Accessibility and performance:** check larger text, focus order, touch targets, and screen-reader flows; reduce idle redraw work and measure response/frame sizes before growing the map.
- **Repository hygiene:** automated tests on pushes/PRs, contribution instructions, issue templates, and an owner-selected license. These are proposed follow-ups, not included in this documentation/Git setup change.

## Scope to defer

An infinite world, combat, trains, multiplayer, a broad modding API, and arbitrary Python execution each introduce significant additional systems. They do not help validate the first programmable production chain. Keep them out of the next prototype and revisit them when playtests justify the complexity.
