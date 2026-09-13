# Configurable crop care

**Implemented:** optional fertilizer, irrigation, and soil-health systems in both Home farm and Breadworks. Each chapter keeps its own options, equipment, supplies, and growing goals.

## Choose your challenge

Open **Growing options** above the field and switch any combination on or off. Changes apply between runs without resetting progress or consuming ticks. All options default to **off**, including for older saves. Turning them off suspends their rules and retains supplies and equipment.

| Option | Adds | When off |
| --- | --- | --- |
| Fertilizer | Consumable feeding, faster growth, harvest bonus, supply purchases. | No boost or harvest bonus. Unused boost timers pause; harvesting clears treatment. |
| Irrigation | Placeable sprinklers, a shared tank, refill trips, pump control, water consumption. | Sprinklers stop and tank water is retained. Manual `water()` returns to its original free behavior. |
| Soil health | Nutrient depletion, slow growth in depleted soil, compost from crop residue. | Soil values are retained but depletion/slowdown/residue collection stop. |

The options are independent. Try irrigation alone for a transport puzzle, soil health alone for a recycling loop, or all three for a complete crop-care routine. They work alongside the Breadworks machines and delivery goals.

## Fertilizer

Each chapter begins with 6 stored doses. `fertilize()` consumes one dose on the current **growing, not yet ripe** crop. Each crop can be treated once. It restores 10 nutrients (up to 100) and gives 6 action ticks of growth boost, counting the fertilize action itself.

While watered, a boosted crop grows by 2 stages per eligible growth tick instead of 1. Boost time also elapses while dry, so water before feeding. Soil-health slowdown, if enabled, still limits depleted crops to even-numbered world ticks.

A treated crop earns its harvest bonus while Fertilizer is on, even after its timed growth boost expires:

- Home farm: normal sale value plus half that value rounded down; wheat sells for 7 instead of 5, carrots for 18 instead of 12, sunflowers for 30 instead of 20.
- Breadworks: 4 wheat instead of 3 in cargo. Use `get_yield()` in capacity checks.

Buy fertilizer at the **supply well, (0, 0)** using `buy_fertilizer(amount)`. Each dose costs 2 coins; store at most 100. Purchases take one action. A full shed, insufficient funds, wrong location, or invalid amount leaves supplies and coins unchanged.

## Irrigation

`install_sprinkler()` costs 8 coins and places a sprinkler on the current growing plot. It can coexist with a crop. Up to 9 sprinklers are allowed, with one per plot. They share a tank containing up to 60 water units.

A sprinkler covers the square consisting of itself and its eight neighbors, clipped to the growing area. Every sixth **world tick**, an enabled pump checks sprinklers in installation order. Each sprinkler with plots below 12 moisture spends 1 tank water and sets those plots to 12 moisture. Normal growth then runs, reducing moisture to 11 on that action. Overlapping coverage does not water the same plot again once it reaches the threshold. If the tank empties, remaining sprinklers wait for another pulse after a refill.

With Irrigation on, manual `water()` costs 2 tank units and still supplies 24 moisture. This allows precise watering but makes well visits part of the programming problem. `refill_tank()` fills the tank for free at (0, 0), taking one action; a sprinkler pulse on that action may immediately use some of it.

`set_irrigation(False)` pauses the pump while keeping the irrigation system's resource rules enabled. `set_irrigation(True)` resumes it. Turning off the Irrigation option suspends the entire system and restores free manual watering. The remembered pump setting is retained when the option is re-enabled.

Sprinklers run during all drone actions, including factory deliveries, and stop advancing during browser waiting or paused playback. Their canvas animation is decorative; the authoritative counters change only on simulation actions.

## Soil nutrients and compost

Each plot starts at 100 nutrients. Harvesting with Soil health enabled removes nutrients according to the crop: wheat 20, carrots 30, sunflowers 15. The same harvest adds one compost, representing crop residue, to a shared supply capped at 1,000.

Below 30 nutrients, crops only grow on even-numbered world ticks. They still need moisture; they never die. This makes depleted soil slower without creating a permanent dead end.

Use `compost()` on soil below 100 nutrients. It consumes one compost, restores up to 40 nutrients, and takes one action. It works on empty or planted growing plots. Fertilizer, if separately enabled, restores an additional 10 nutrients per treatment.

## Implemented commands and sensors

| Call | Behavior |
| --- | --- |
| `fertilize()` | Feed this growing crop once; consume one dose. |
| `buy_fertilizer(4)` | Buy fertilizer at (0, 0), 2 coins each. Positive integer amount, at most 100. |
| `compost()` | Consume one compost and restore up to 40 nutrients. |
| `install_sprinkler()` | Build on the current growing plot for 8 coins. |
| `refill_tank()` | Refill to 60 at (0, 0), before this action's world systems advance. |
| `set_irrigation(True)` | Enable the pump; `False` pauses it. |
| `feature_enabled("soil")` | Read `"soil"`, `"fertilizer"`, or `"irrigation"`. |
| `get_nutrients()` | Current plot nutrients, 0–100. |
| `get_supply("water")` | Read shared `"water"`, `"fertilizer"`, or `"compost"` stock. |
| `has_sprinkler()` | Whether this plot has an installed sprinkler, even if disabled. |
| `is_fertilized()` | Whether this crop has been treated, even if the option is disabled. |
| `get_yield()` | Wheat per factory harvest: 3 or 4; Home farm returns one crop. |
| `get_scenario()` | `"classic"` or `"factory"`, for reusable scripts. |

All six new actions cost one tick on success. Queries cost no ticks and consume interpreter operations. The 400-action and 20,000-operation limits remain unchanged. Actions for disabled systems give an actionable error instead of silently changing the game.

A sensor-based care fragment, run on a growing plot:

```python
if feature_enabled("soil") and get_nutrients() <= 60:
    if get_supply("compost") > 0:
        compost()

if feature_enabled("fertilizer") and get_crop() != None:
    if not can_harvest() and not is_fertilized():
        if get_supply("fertilizer") > 0:
            fertilize()
```

## Examples and extra goals

**Smart crop care** is available in both chapter example menus. It tends six plots, checks nutrient levels, fertilizes when supplies permit, installs two row sprinklers when affordable, restocks at the well, and unloads factory cargo when needed. Run it repeatedly; the next cycle harvests the crops you just raised. If factory storage is full, it asks you to process stock before continuing.

**Sprinkler network** installs 3×3 coverage across the growing area as funds allow, refills the tank, and demonstrates a bounded pump/refill routine. Existing sprinklers continue working when you later load a different farm or factory program.

Three independent growing goals pay once per chapter: fertilize 6 crops (+20 coins), have sprinklers replenish 36 plot moisture readings (+25), and compost 6 plots (+30). Waterings of empty growing plots also count. Completed goals and counters persist when options are off. They do not replace the chapter mission campaign.

## Compatibility and design

World schemas retain their existing chapter versions and gain a versioned `care` extension. Saves without this extension migrate to disabled options, healthy soil, starter supplies, and no equipment. Present but malformed extensions are rejected. Expansion remaps soil and sprinklers by coordinate, and factory validation restricts them to its 24 growing plots. Portable export/import preserves both chapters' settings.

The requested reference, [The Farmer Was Replaced's Steam description](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/), emphasizes gradual introduction of programming, resource-funded technology, and continuous progression. Sprout uses those broad lessons for its own optional care systems and production chain. The mechanics and numbers above are original game rules; the store description was not used as evidence that the reference implements these exact systems.

Continuous controllers, weather, pests, crop diseases, and industrial compost/fertilizer production remain possible later additions. They are not implemented by these toggles.
