# Player guide and Python API

## Start playing

Run `python3 run.py` from the project directory and visit `http://127.0.0.1:8000`. Python 3.10+ and a modern browser are required. No `pip install` or npm build is needed.

The game has two chapters with independent saves. Choose **The Breadworks** at the top to try factory logistics; see its guide below.

In **Home farm**, you start with 20 coins, a 6×6 field, and three ripe wheat plots. Your drone is at `(0, 0)`. Click **Run code** to run the starter program. It harvests the ripe wheat, tills empty ground, plants six wheat seeds, waters the row, and moves back to the first plot. Expected result: **49 coins, 3 harvested crops, 6 planted crops, 27 ticks**, and the first mission complete.

## Controls

| Control | Behavior |
| --- | --- |
| Run mode | Bounded run (up to 400 actions) or Continuous (resumable long-running program). |
| Run code | Start the selected execution mode from the current field. |
| Pause / Resume | Freeze the displayed farm, then continue the same program. |
| Step | Prepare a run if needed and perform one drone action. |
| Stop | Clear queued commands or the continuous checkpoint. Keep displayed farm progress. |
| Speed | Set animation speed to 1×, 2×, 4×, or 8×. Game outcomes are unchanged. |
| Load example | Replace editor text with a working example; it does not reset the farm. |
| Select a tile | Inspect a plot without moving the drone. |
| Inspect plots | Open a text table of the full field, including moisture and drone position. |
| Room to grow | Spend coins on new crops or field expansion. Available between runs. |
| Reset arrow / New farm | Reset only the active chapter after an in-game confirmation. |
| Chapter buttons | Switch between Home farm and Breadworks between runs; each keeps its own program and speed. |

Keyboard: **Ctrl/Cmd + Enter** runs, pauses, or resumes. **Tab** indents by four spaces; **Shift + Tab** removes indentation. Enter copies the previous line's indentation and adds four spaces after a colon. Dialogs close with Escape. Controls work without interacting with the canvas.

## Home farm crop lifecycle

These are the default rules. Optional [crop-care systems](CROP_CARE.md) change fertilizer bonuses, water supply, and soil nutrients when enabled.

```python
# Use an empty plot first.
till()
plant("wheat")
water()
while not can_harvest():
    wait()
harvest()
```

Each successful action advances one tick. Water lasts for 24 ticks, including the tick of the `water()` command. Crops grow once per action while watered, then stop growing when dry. Mature crops never wilt. Working on other plots grows all watered crops simultaneously.

Planting costs coins, harvesting sells the crop automatically, and seeds are purchased automatically when planted. There is no separate inventory. If your balance is zero, a wheat seed is free so you can recover. The drone has unlimited solar power. Water refills are only needed when the optional Irrigation system is enabled.

| Crop | Seed cost | Sale value | Growth ticks | Unlock cost |
| --- | --- | --- | --- | --- |
| `"wheat"` | 1 | 5 | 6 | Available initially |
| `"carrot"` | 3 | 12 | 9 | 40 |
| `"sunflower"` | 5 | 20 | 12 | 100 |

More land costs 150 coins and expands the field to 8×8. Existing crops retain their coordinates. Use `get_size()` rather than hardcoding the width so programs adapt automatically.

## Home farm commands

All commands below return `None` and cost one tick on success. An invalid command stops the program with an error and costs no tick.

| Command | Purpose and conditions |
| --- | --- |
| `move("north")` | Move one plot north; also accepts `"south"`, `"east"`, `"west"`. |
| `till()` | Prepare the current empty plot. Already-tilled empty soil is allowed. |
| `plant("wheat")` | Plant an unlocked crop in empty, tilled soil; also `"carrot"`, `"sunflower"`. |
| `water()` | Set the current plot's moisture to 24 before the action tick. Can water empty soil. |
| `harvest()` | Sell the current ripe crop. Soil stays tilled and retains remaining water. |
| `wait()` | Advance one tick without moving. |

The northwest corner is `(0, 0)`. East increases x and south increases y. The farm wraps at every edge: moving west from x=0 places the drone at x=`get_size() - 1`.

## Queries

Queries take no arguments and do not advance time.

| Query | Result |
| --- | --- |
| `can_harvest()` | `True` if the current plot has a mature crop. |
| `get_crop()` | `"wheat"`, `"carrot"`, `"sunflower"`, or `None`. |
| `get_water()` | Remaining water ticks, from 0 to 24. |
| `is_tilled()` | Whether the current plot has prepared soil. |
| `get_x()`, `get_y()` | Current drone coordinates. |
| `get_size()` | Field width/height: 6 or 8. |
| `get_coins()` | Current coin balance. |

## Python language support

Supported: comments, numeric/string/boolean/None values, name assignments, `+=` and other supported augmented arithmetic, lists/tuples, integer indexing, `+ - * / // %`, comparisons, membership, boolean `and/or/not`, `if/elif/else`, `for`, `while`, loop `else`, `break`, `continue`, `pass`, top-level functions, positional parameters, and `return`. Boolean expressions short-circuit. Functions use local names with global fallback; the implementation does not emulate every CPython scoping detail.

Built-in helpers: `range`, `len`, `min`, `max`, `abs`, `int`, `str`, `print`. `min` and `max` accept numbers or a numeric list, tuple, or range. `print` accepts multiple positional values. Lists are read-only: mutation, append, and unpacking are not supported. `str`/`print` abbreviate large nested collections. Calls use positional arguments only.

Unavailable: imports/packages, objects/attributes/methods, file/network access, classes, decorators, annotations, lambdas, comprehensions, slicing, exponentiation, f-strings, string `%` formatting, keyword/default/variadic function arguments, nested function definitions, exception handling, `global`, `nonlocal`, and arbitrary Python execution.

Each **Bounded run** has limits of **400 drone actions**, **20,000 interpreter operations**, **16,000 source characters**, and **100 print calls**. Use finite cycles and rerun them. Even a loop without actions is bounded. Run-local variables reset on each new run; the farm persists. In Continuous mode, variables and program position persist between actions and across reloads. Its 20,000-operation and 100-message budgets renew after each action. See [Continuous automation](CONTINUOUS.md) for limits and recovery.

## Home farm example progression

1. **Your first row:** earn the first mission reward and learn the commands.
2. **The whole field:** nested loops plant and water the full field. This completes the planting mission.
3. **Harvest & replant:** a function tends every plot. Run it repeatedly to earn more income.
4. Unlock carrots, then run **A carrot patch**. It harvests six carrots one at a time, paying for each next seed.
5. Unlock sunflowers and expand the farm. Try modifying `plant("wheat")` in the maintenance routine to grow your new crop.

The four missions reward harvesting 3 crops (+20), planting 12 (+25), harvesting 6 carrots (+60), and earning 200 crop-sale coins (+100). They complete in order, and earlier statistics still count when the next mission becomes active. After all missions, the farm remains playable as a sandbox.

## Errors, saves, and troubleshooting

- **Nothing ripe here:** use `can_harvest()` before harvesting. Water a growing crop and spend ticks working elsewhere or waiting.
- **Needs prepared soil:** call `till()` before planting.
- **Already has a crop:** harvest the existing crop first; tilling never destroys it.
- **Crop locked:** purchase it in Room to grow between runs.
- **Operation/action limit:** use a smaller finite loop, then run the next cycle.
- **Syntax error:** check colons, indentation, spelling, and the supported language list. The activity log gives the source line.
- **Cannot reach Python:** keep `python3 run.py` running. If its port is busy, choose `--port 8080` and open the matching URL.
- **Save not appearing:** saves are specific to this browser, host, and port. `localhost:8000` is different from `127.0.0.1:8000`.

Progress and code save to browser storage. Refreshing during a run keeps displayed actions and discards its remaining queue. Stopping does the same. Clearing browser data or resetting the farm removes current progress. There is no cloud backup. Invalid saves are rejected with a visible notice; use a single tab to avoid last-write-wins conflicts.

## Portable saves

Use **Export save** in the footer to download a JSON backup. Use **Import save**, select that file, review its summary, then choose **Restore save**. Invalid files leave your progress unchanged. Restoration keeps the previous save in the device-local `sprout.save.backup` storage key; export first for an accessible copy. Old single-farm saves migrate automatically. Downloads require browser support; use a regular browser if an embedded browser does not handle downloads.

## The Breadworks — factory chapter

Select **02 · The Breadworks**. You start with a separate 8×8 map, 30 coins, four ripe wheat plots, an empty drone, and 12 wheat in the chest. Your classic farm is kept.

Start with **First bread**. From a fresh chapter this performs 60 actions, makes 4 flour, bakes and delivers 4 bread, and completes three missions. You finish with **127 coins**, 4 wheat still in the chest, empty cargo, and the drone at the depot.

### Your next playable goals

1. Run **Harvest & store** to tend all 24 growing plots. Run again to gather more wheat. If storage fills, the script stops safely and prompts you to process stock.
2. Buy **Bigger cargo** for 50 coins. Larger batches reduce trips between the field and chest.
3. Run **Farm to bakery** repeatedly. It tends the first row and overlaps transport with processing. Complete the 12-harvest, 20-delivery, and 50-delivery missions.
4. Buy **Quick mill** (75 coins) and **Hotter oven** (90 coins). They halve the duration of future batches.
5. Stock at least 24 wheat, click **Start order**, then try **Order runner**. Deliver 12 bread within 180 action ticks for 40 bonus coins. Improve the program and beat your own record.

Examples run from current state. First bread is an opening tutorial; later scripts are repeatable controllers. A partially supplied machine or unusual cargo can require adjusting quantities. Stop preserves what you have already seen, so inspect inventory before restarting a tutorial that assumes empty buffers.

### Map and transport

| Location | Coordinates | Purpose |
| --- | --- | --- |
| Growing field | x 0–5, y 0–3 | 24 plots for wheat. |
| `"chest"` | (0, 6) | 48 total items; wheat, flour, and bread share capacity. |
| `"mill"` | (3, 6) | 2 wheat → 1 flour; 4 ticks, or 2 after upgrading. |
| `"oven"` | (6, 6) | 1 flour → 1 bread; 6 ticks, or 3 after upgrading. |
| `"depot"` | (7, 3) | Sell delivered bread for 8 coins each. |
| Rocks | (6,2), (6,3), (3,4) | Block movement and planting. |

Navigate directly onto a building pad to transfer cargo. Factory edges **do not wrap**. `navigate_to()` finds a shortest route around rocks, expanding into ordinary one-tile moves. Each step costs one action/tick; already standing at the destination costs zero. `get_size()` returns the whole map size (8); growing loops should use width 6 and height 4.

### Cargo and production

Harvesting yields **3 wheat into cargo** and requires 3 free slots. It does not sell the crop. Planting still costs 1 coin, with emergency free wheat at zero. Tilling, growth, and moisture follow the same rules as Home farm, restricted to growing plots.

The drone carries 8 total items, or 16 after its upgrade. Both machines hold 12 input items and 8 finished products. A transfer uses a positive integer amount and either completes in full or fails without changing items or time. Machine ingredients can be supplied but cannot be taken back out; only finished products can be loaded. Use the chest to store any of the three item types.

Each successful movement, farming action, transfer, or `wait()` advances both machines and all watered crops once. A machine consumes ingredients when it starts a batch; that action is its first processing tick. Outputs are available to the next command. A full output buffer stops new batches without consuming input. Inputs and completed output in the dashboard exclude ingredients already inside an active batch. Save/reload keeps those active batches intact.

The panel distinguishes **Working**, **Waiting for wheat/flour**, **Output full**, and **Ready** (enough input; take an action to start). Machine upgrades affect the next batch. Queries, upgrades, starting an order, switching chapters, and wall-clock waiting cost no simulation ticks.

### Implemented factory API

The existing farming commands, state queries, Python helpers, and interpreter limits remain available. These additions only work in Breadworks:

| Call | Result / effect |
| --- | --- |
| `navigate_to("mill")` | Move to a named building via visible route steps. Also accepts chest, oven, depot. |
| `navigate_to(x, y)` | Move to walkable coordinates, integers 0–7. |
| `load("wheat", 4)` | Load from current chest or a machine's output; needs enough available stock and cargo space. One tick. |
| `unload("wheat", 4)` | Store at chest, supply matching machine ingredient, or sell bread at depot. One tick. |
| `cargo("wheat")` | Carried quantity of wheat, flour, or bread. |
| `cargo_space()` | Total free drone slots across all items. |
| `stored("mill", "flour")` | Stored quantity of this item at the named entity. Mill wheat/oven flour read input; mill flour/oven bread read completed output. Depot returns 0. |
| `free_space("mill", "wheat")` | Available input capacity for this item. Unsupported machine ingredients return 0. Chest capacity is shared; depot is not accepted. |
| `machine_status("oven")` | `"working"`, `"waiting_input"`, `"output_full"`, or `"ready"`; accepts mill or oven. |
| `get_tick()` | World tick count. |
| `get_delivered()` | Lifetime bread delivered. |

Queries are instantaneous in game time, but consume interpreter budget. A polling loop must include `wait()` or another action; repeatedly checking a machine does not make it work. Supply ingredients before waiting for output.

### Orders, missions, and troubleshooting

Six missions reward 4 flour (+15), 4 baked bread (+20), 4 delivered bread (+30), 12 harvested plots (+40), 20 delivered bread (+80), and 50 delivered bread (+150). Earlier progress counts. Rewards pay in sequence once.

Timed orders unlock after 4 bread delivered. They count bread delivered **after** the order starts, including products you stockpiled earlier. Deliver 12 within 180 action ticks; the final tick counts. A successful order pays 40 coins once and records the best time. An expired order has no penalty beyond missing the bonus. Start or retry between runs; no second order can start while one is active.

- **Cargo full:** use `cargo_space()`; harvest needs three slots. Unload wheat into chest or mill.
- **Input full / wrong item:** use `free_space(entity, item)` and match the recipe. The oven accepts flour; the depot only buys bread.
- **Output full:** collect finished products so the machine can start its next batch.
- **Waiting for input:** supply ingredients; waiting alone cannot create wheat or flour.
- **Chest full:** run the production routine before harvesting more. Stock occupies real capacity.
- **Rock or edge:** use `navigate_to()` or change the manual route. Factory movement never wraps.
- **Order failed:** stock ingredients first, increase batch sizes, overlap machine work, and reduce empty trips. Progress and coins from regular sales are kept.

Export/import includes both chapters, their code, and playback speeds. Save files must be under 590 KB; the server allows 600 KB for save validation to accommodate both programs and continuous checkpoints. The run API still has its original 100 KB request limit.

## Optional growing systems

Open **Growing options** above the field. Fertilizer, Irrigation, and Soil health can each be enabled independently in either chapter. Defaults are off; old saves keep their original rules. Changes are available between runs and do not reset equipment or supplies.

The **Smart crop care** example automates nutrients, fertilizer, watering, well visits, and factory cargo checks. **Sprinkler network** installs automated watering coverage as funds allow. These are two additional shared examples alongside the four chapter-specific examples.

See [CROP_CARE.md](CROP_CARE.md) for the complete rules, costs, sensor API, toggle behavior, and three optional growing goals. The in-game **Growing systems** guide contains the same operational reference. With options on, older simple examples may need supply and yield checks; use the new examples as starting points.

## Continuous autopilot

Load **Continuous autopilot** to select Continuous mode and start a repeating six-plot farming routine. In Breadworks it also processes wheat and flour and delivers bread. Both examples handle any combination of growing options. Pause and Step preserve your place; Stop lets you edit. Reload restores paused, even after restarting Python. Nothing grows while the page is closed. See [the complete guide](CONTINUOUS.md).

## Example helpers and activity log

`store_cargo()` is defined inside **Harvest & store**; it is not a built-in API. Copy its `def store_cargo():` block along with `tend_field()` and the final `tend_field()` call. Load the complete example if your edited copy is missing those helpers. A full chest exits the routine safely; process inventory before harvesting again.

The activity log keeps its latest 150 entries in a fixed-height scroll area. Long output wraps inside the panel. Scroll up to read earlier entries without being pulled back down; **Latest ↓** returns to live updates. The log can receive keyboard focus for scrolling.
