# Crop recycling — implemented

Breadworks can now turn harvest residue into crop-care supplies. This optional chain adds transport, shared buffer limits and a choice between restoring soil and producing fertilizer. Home farm and fixed challenge scenarios keep their existing rules.

## Play it

1. In **The Breadworks**, Stop any running or paused program. Open **Crop recycling**, below the bakery production panel, and enable its switch.
2. Load **First recycled fertilizer**. It harvests two plots and returns **one compost and two fertilizer** to the supply well. On a fresh farm it takes 52 actions with all growing options off. It checks capacities and exits with advice when existing stock prevents progress.
3. Enable **Soil health** and/or **Fertilizer** in Growing options to use those supplies on crops. Recycling works independently of both settings.
4. Load **Recycling autopilot** to select Continuous mode. It grows one row, delivers bread, transports residue, keeps a small compost reserve and makes fertilizer when that growing option is on. It refills irrigation water as needed and does not purchase fertilizer.
5. Inspect the new buffer cards, paused/working/blocked status, lifetime production counts and return goals. The goals track returning 4 compost and 8 fertilizer; they have no coin rewards.

The original continuous and team starters still demonstrate the original bakery/care loop. With recycling enabled, customize them to clear the residue hopper and return compost, or use the new autopilot. Otherwise the hopper eventually fills. The recycler autopilot is a **solo example**; all new transport calls are also supported in your two-drone programs.

## Rules and recipes

Each successful wheat harvest puts **one residue** into the shared hopper at the supply well `(0, 0)`. Residue does not occupy harvest cargo. Wheat still yields 3, or 4 when fertilized. Residue collection works with Soil health on or off. Enabling recycling does not create residue from earlier harvests.

| Building | Position | Recipe / purpose | Capacity | Time |
| --- | --- | --- | --- | --- |
| Supply well | `(0, 0)` | Collect residue; receive finished care supplies | 48 residue, 1,000 compost, 100 fertilizer | Transfers take one action |
| Composter | `(1, 5)` | 2 residue → 2 compost | 12 input / 8 output | 6 world ticks |
| Fertilizer mixer | `(5, 5)` | 1 compost → 2 fertilizer | 12 input / 8 output | 4 world ticks |

The well shares a growing plot and the existing irrigation refill location. Crops and farming there still work. The two machines start on the lane pads above. Installed composter/mixer pads can move through [Workshop layouts](LAYOUTS.md), even while paused. The well and recipes stay fixed; construction, recycling-machine upgrades and conveyors are not included.

With recycling enabled, Soil health still depletes nutrients but **no longer gives instant compost** when harvesting. Byproducts instead travel through the composter. This avoids collecting both instant compost and industrial compost from the same harvest. Recycling disabled keeps the original instant-compost rule. Home farm always keeps that rule.

One compost can restore up to 40 nutrients with `compost()`. Converting it produces two fertilizer doses; each dose restores up to 10 nutrients, speeds a growing crop and increases wheat yield to 4. Both actions require their respective Growing option. You choose how to split the composter's output.

## Transport API

These are extensions of **existing implemented commands**, not new host-Python functions:

| Call | Behavior |
| --- | --- |
| `feature_enabled("recycling")` | Check this Breadworks campaign option, without ticking. Returns False before installation. |
| `navigate_to("well")`, `"composter"`, `"mixer"` | Reach a new named pad after recycling has been enabled at least once. Each movement step takes one tick. |
| `load("residue", 2)` at well | Take two items out of the hopper into cargo. |
| `unload("residue", 2)` at composter | Supply its input. Unloading residue at the well returns it to the hopper. |
| `load("compost", 2)` at composter | Collect finished output. Active batches are excluded. |
| `unload("compost", 1)` at mixer | Supply fertilizer production. |
| `load("fertilizer", 2)` at mixer | Collect two finished doses. |
| `unload("compost", n)` or `unload("fertilizer", n)` at well | Return products to the shared care store. `get_supply()` reads these; `compost()` / `fertilize()` consume them. |
| `stored("composter", "compost")` | Read finished output; with residue reads unconsumed input. Same pattern for the mixer. |
| `stored("well", "residue")` | Read hopper stock. With compost/fertilizer reads shared care stock, including initial or purchased supplies. |
| `free_space("well", "fertilizer")` | Read room for returned doses. Same pattern for compost or residue. |
| `free_space("composter", "residue")` | Read ingredient input room. Unsupported ingredients return zero. |
| `machine_status("composter")` / `"mixer"` | `working`, `waiting_input`, `output_full`, `ready`, or `paused` when recycling is off. |

`cargo()` and the chest support **wheat, flour, bread, residue, compost, fertilizer** after installation. All items share the same 8/16 cargo capacity and 48 chest slots. Transfers require positive integer amounts and enough source stock, destination room and cargo space; a failed transfer changes no stock or time. The depot continues to buy bread only. Returned or purchased care supplies **cannot be loaded out of the well**; only new machine products and chest stock can circulate. This prevents counting an existing dose again as a newly produced byproduct.

Minimal fragment, assuming two residue available and capacity at both ends:

```python
if feature_enabled("recycling"):
    if stored("well", "residue") >= 2:
        if cargo_space() >= 2 and free_space("composter", "residue") >= 2:
            navigate_to("well")
            load("residue", 2)
            navigate_to("composter")
            unload("residue", 2)
```

## Bottlenecks, clock and controls

- A full 48-item hopper blocks harvesting **before any crop, cargo, soil or tick changes**. Transport residue to free room, or Stop and pause recycling.
- Each machine consumes input at batch start and reserves **two output slots**. Seven output items already block a new batch even though one slot remains. Collect products to resume production.
- The transfer action that starts a batch is its first tick. Machines advance once per world tick, including farming, navigation and waits. Queries, elapsed browser time and Pause add no ticks. Two drone actions still advance the machines once.
- Compost/fertilizer carried in cargo are not usable growing supplies until returned to the well. Both drones can then use them; a parked drone retains its own cargo.
- Stop before toggling. Disabling pauses new machines and residue collection, retains stock and exact batch time, and permits transfers for cleanup. Re-enabling resumes. It changes neither growing options nor existing crops, coins, bakery machines or time.
- If Soil health and Fertilizer are both off, the autopilot stores compost without consuming it. Supplies are bounded. Enable a useful care option, adapt your storage/production controller or pause recycling before stock fills. No waste-destruction command or infinite sink is included.

The efficiency dashboard still measures the **mill and oven**. Recycling has live buffers and status cards rather than separate machine utilization graphs. Fixed challenges do not allow this module, so existing trial scores remain comparable.

## Saves and conservation

World and portable envelope versions stay unchanged. The optional `recycling.version = 1` contains the enabled flag, residue hopper, two input/output/remaining machine records and five lifetime counters: residue collected, compost/fertilizer produced and compost/fertilizer returned. Installation adds three zero-valued item keys to cargo, chest and an existing parked drone. Validation retains absent extensions absent, preserving old solo/team checkpoint digests and inventory maps.

Every saved recycling world must conserve material. In half-residue units, residue and compost each weigh 2, fertilizer weighs 1. The sum across hopper, inventories, buffers, reserved in-flight ingredients and cumulative returns must equal twice the collected residue. Returns leave the logistics line and enter the care store; later crop consumption does not remove them from the cumulative ledger. Initial fertilizer, bought doses and instant compost from disabled recycling are outside this ledger. Malformed extensions, overfilled stock, lost/duplicated material and impossible reserved output fail validation without changing the input save.

Portable solo/team continuations preserve new materials and active batches and restore paused. No interpreter commands, compiler version, unrestricted code execution, offline simulation or hosting boundary changed. Player saves remain editable local data rather than an anti-cheat system.

## Validation and later scope

Regression coverage includes all eight care combinations, per-step conservation, atomic capacity failures, output reservations, pause/resume, old and new checkpoints, team contention, usable returned supplies and HTTP configuration. In an additional 1,800-tick playtest, all eight autopilot variants delivered 54–61 bread; fertilizer-enabled variants returned 40–48 manufactured doses. These are example results, not fixed challenge scores or an optimal strategy.

Existing machines can now move through [Workshop layouts](LAYOUTS.md). Extra buildings, conveyors, new recycling challenges, power and recipes remain separate proposals in [ROADMAP.md](ROADMAP.md).
