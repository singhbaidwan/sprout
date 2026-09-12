# Player guide and Python API

## Start playing

Run `python3 run.py` from the project directory and visit `http://127.0.0.1:8000`. Python 3.10+ and a modern browser are required. No `pip install` or npm build is needed.

You start with 20 coins, a 6×6 field, and three ripe wheat plots. Your drone is at `(0, 0)`. Click **Run code** to run the starter program. It harvests the ripe wheat, tills empty ground, plants six wheat seeds, waters the row, and moves back to the first plot. Expected result: **49 coins, 3 harvested crops, 6 planted crops, 27 ticks**, and the first mission complete.

## Controls

| Control | Behavior |
| --- | --- |
| Run code | Compile a bounded run from the current field; animate its commands. |
| Pause / Resume | Pause or resume the queued commands. |
| Step | Prepare a run if needed and perform one drone action. |
| Stop | Discard queued commands. Keep only the progress already displayed. |
| Speed | Set animation speed to 1×, 2×, 4×, or 8×. Game outcomes are unchanged. |
| Load example | Replace editor text with a working example; it does not reset the farm. |
| Select a tile | Inspect a plot without moving the drone. |
| Inspect plots | Open a text table of the full field, including moisture and drone position. |
| Room to grow | Spend coins on new crops or field expansion. Available between runs. |
| Reset arrow / New farm | Start fresh after an explicit in-game confirmation. |

Keyboard: **Ctrl/Cmd + Enter** runs, pauses, or resumes. **Tab** indents by four spaces; **Shift + Tab** removes indentation. Enter copies the previous line's indentation and adds four spaces after a colon. Dialogs close with Escape. Controls work without interacting with the canvas.

## Crop lifecycle

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

Planting costs coins, harvesting sells the crop automatically, and seeds are purchased automatically when planted. There is no separate inventory. If your balance is zero, a wheat seed is free so you can recover. The drone has unlimited solar power and water; there are no refill chores in this version.

| Crop | Seed cost | Sale value | Growth ticks | Unlock cost |
| --- | --- | --- | --- | --- |
| `"wheat"` | 1 | 5 | 6 | Available initially |
| `"carrot"` | 3 | 12 | 9 | 40 |
| `"sunflower"` | 5 | 20 | 12 | 100 |

More land costs 150 coins and expands the field to 8×8. Existing crops retain their coordinates. Use `get_size()` rather than hardcoding the width so programs adapt automatically.

## Commands

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

Each run has limits of **400 drone actions**, **20,000 interpreter operations**, **16,000 source characters**, and **100 print calls**. Use finite cycles and rerun them. Even a loop without actions is bounded. Run-local variables reset on each new run; the farm persists.

## Example progression

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
