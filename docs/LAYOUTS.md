# Workshop layouts

Implemented 2026-10-03. Layout planning makes transport distance a player decision in the Breadworks campaign. It relocates existing machines between programs; extra machines, construction costs, conveyors and power remain future scope.

## Plan, apply and measure

1. **Stop** the program, including a paused Continuous or team controller.
2. Open **Workshop layout** below the map. Choose a machine, then a numbered lane pad. The canvas outlines the selected preview pad.
3. Inspect **Transport distances**: current and proposed shortest tile moves around rocks. Compact workshop and Default layout create editable previews. Discard preview restores saved positions.
4. **Apply layout** moves all previewed machines together. Stock cards, labels, inspection and named Python destinations update immediately. Preview alone changes no world state.
5. Load **Layout delivery test** in Bounded run. It feeds four flour individually from mill to oven, then delivers four loaves. It requires eight chest wheat, eight free cargo slots and empty mill/oven buffers with no active batch. Failed prerequisites print an explanation without taking an action.

Export your save before comparing; import it to restore the same stock, drone position, upgrades and care settings. The fresh-farm program completes in **54 ticks with defaults** and **48 ticks with Compact workshop**. These are example baselines, not optimal strategies. Shorter trips also give machines less processing time; distance alone does not prove higher throughput. Restart the efficiency measurement window to compare sustained production from identical conditions.

Existing solo, team and recycling examples use named machine routes. Hardcoded `navigate_to(3, 6)` still means those literal coordinates; update such programs yourself. No player Python function is added.

## Placement rules

| Building | Default position | Can move? |
| --- | --- | --- |
| Grain chest | (0, 6) | Fixed supply anchor |
| Mill | (3, 6) | Yes |
| Oven | (6, 6) | Yes |
| Depot | (7, 3) | Fixed delivery anchor |
| Supply well | (0, 0) | Fixed, available after installing recycling |
| Composter | (1, 5) | Yes after installing recycling |
| Fertilizer mixer | (5, 5) | Yes after installing recycling |

- Coordinates are integers 0–7. Pads must lie outside the 24 growing plots (x 0–5, y 0–3), away from rocks and other buildings.
- Uninstalled composter/mixer pads stay reserved to prevent overlaps on later enablement. Once installed, both can move even while recycling is paused; vacated pads become available.
- Pads are passable docking locations. Terrain, obstacles and farming boundaries remain fixed.
- Moves cost no coins and no ticks. Inventories, active batches, missions, measurements, both drone positions and cargo, and growing options are preserved exactly.
- Finish an active delivery order before applying. Planning remains available during an order. Challenges reject layout configuration and saved layout extensions, including empty ones.
- Stop first: a checkpoint is bound to its exact world and may contain a route to an old pad. Applying after Stop starts the next program with fresh navigation.

## Save and HTTP contract

Existing version 2 factory worlds may carry this optional version 1 extension:

```json
"layout": {
  "version": 1,
  "positions": {
    "mill": {"x": 1, "y": 6},
    "oven": {"x": 2, "y": 6}
  }
}
```

At most four movable overrides are allowed; absent names use defaults. Validation requires exact extension/coordinate keys, rejects boolean/float coordinates and checks all resolved buildings for overlaps. Recycling validates first, so its machines require an installed extension. Malformed present layouts fail rather than silently reverting.

Untouched worlds keep the extension absent, preserving old solo/team controller hashes. Validation retains present empty extensions because normalization would change checkpoint digests. Configuration removes default-coordinate overrides; restoring all defaults removes the extension. Campaign saves and portable solo/team continuations retain layouts and load paused as usual. No envelope version change is needed.

`POST /api/layout` accepts `{state, positions}` and returns `{state, message}`. `positions` is the **complete sparse override map replacing the old map**, rather than a partial patch. `{}` restores defaults. The server validates the copied world and all destinations before mutation, allowing batch swaps without transient overlaps. Invalid requests return HTTP 400. The 100,000-byte request limit, loopback/Host/Origin rules and stateless server remain. Browser request tokens discard stale replies.

## Compact preset and validation

Compact workshop previews mill (1,6), oven (2,6), and, when installed, composter (0,4), mixer (1,4). Bakery legs change from **3/3/4** to **1/1/8** moves: easier chest/mill transfer trades off a longer depot trip. Recycling legs change from **6/4/10** to **4/1/5**. The preset starts an experiment; it is not an optimization guarantee.

Tests cover transfers at new/old pads, atomic rejection/swaps, preserved stock/batches, old/custom continuations, team contention with one world phase, fixed trials, HTTP assets/configuration, delivery tests and sustained solo/team/recycling examples. Node checks verify preview routes and reserved pads. Browser checks cover apply/reload, stock preservation, keyboard focus and responsive controls. Additional machines, costs/research, conveyors, storage targets and standalone blueprint artifacts remain proposals in [ROADMAP.md](ROADMAP.md).
