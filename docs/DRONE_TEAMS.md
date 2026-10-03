# Drone teams — implemented

## Play with two drones

1. Open **02 · The Breadworks**. Stop a running or paused program first.
2. Set **Run mode → Drone team (2)**. Your existing Drone 1 program stays in the editor; Drone 2 initially waits.
3. Click **Load team starter** to replace both programs with a cooperating farmer and courier. Export a save first if you want to keep your own scripts.
4. **Run code** starts both. Use **Editing → Drone 1 / Drone 2** to inspect either program. **Pause** freezes the shared world; **Step** performs one team tick. **Stop** keeps farm progress and lets you edit both programs.
5. Return to Bounded run or Continuous to use Drone 1 alone. Drone 2 parks with its cargo and program intact. Select team mode again to reuse it.

Team mode is optional and available immediately in Breadworks. Home farm retains its original single drone. Resetting Breadworks removes its second drone and resets both programs along with the chapter.

## Divide the work

The starter's green **Drone 1** tends the first two field rows and unloads harvests into the chest. The blue **Drone 2** moves grain to the mill, flour to the oven, and bread to the depot. Each has its own cargo capacity (8, or 16 after the cargo upgrade), program variables, position, and navigation route. Coins, machines, chest contents, water, fertilizer, compost, missions, and orders are shared. The starter handles every combination of growing options.

The commands are the existing implemented Python API: `move`, `navigate_to`, `harvest`, `cargo`, `cargo_space`, and so on always refer to the drone running that program. There is no `spawn_drone()` or shared Python variable API. Use inventories and the shared clock to coordinate. The team dashboard displays cargo, completed team actions, and blocked attempts for each drone. Counters accumulate across team runs; solo actions do not increment them.

Try extending the farmer to all four rows, splitting the field between two farmers, or changing courier batch sizes. Compare how many loaves you deliver in the same number of world ticks. Extra drones can expose machine or storage bottlenecks rather than doubling output automatically.

## Clock and contention rules

- Both controllers observe the world at the start of a tick, each with a bounded computation budget. Each produces at most one action, finishes, or reports an error.
- A syntax, computation-budget, or invalid-action error in either program stops the team before committing either action for that tick. Earlier ticks are kept; the error names the drone and source line.
- Actions resolve in alternating priority: Drone 1 first on even starting ticks, Drone 2 first on odd starting ticks. Only one non-movement action can use the same tile or building pad per tick. A drone merely flying through or waiting on a pad does not occupy its work slot.
- Movement still respects map edges and rocks. Drones fly in separate air lanes and may share or cross a tile. Physical collision avoidance and traffic deadlocks are future features.
- A valid action that loses a resource conflict is retried from its previous program checkpoint on the next tick. This repeats the calculations and queries since its last completed action. Query inventory immediately before a transfer, and guard crop actions with conditions. A hard-coded transfer can still fail if its stock is gone on the next tick.
- After resolving both actions, advance irrigation, crop growth, machines, mission rewards, and delivery deadlines **once**. Machine outputs created by this phase become available next tick. Two actions therefore take one tick; a finished drone parks while its partner continues. If both finish without an action, no tick passes.
- World `stats.actions` counts successful commands. World `tick` counts shared rounds, so those totals can differ. Presentation speed only changes browser pacing.

Example for two drones sharing the chest safely:

```python
while True:
    navigate_to("chest")
    amount = min(stored("chest", "wheat"), cargo_space())
    if amount > 0:
        load("wheat", amount)
    navigate_to("mill")
    amount = min(cargo("wheat"), free_space("mill", "wheat"))
    if amount > 0:
        unload("wheat", amount)
    wait()
```

## Save and execution contract

`farm/team.py` plans bounded continuations and resolves commands without host threads. `POST /api/team/step` accepts `{state, codes: [drone1Source, drone2Source], checkpoint?}` and returns `{state, checkpoint, revision, done, error, frames, actions, operations, drones}`. Frames contain labeled messages; the top-level state is the single committed world snapshot. Requests are stateless, deterministic, and limited to 600 KB.

Each program retains the continuous interpreter's limits: 16,000 source characters, 20,000 operations and 100 prints between actions, and 48 KB of continuation data. The team continuation is version 1, limited to 100 KB, and binds both sources and the full world. It contains a monotonically increasing response revision and two `{done, checkpoint}` records. Source is compiled again on resume; saves never provide executable bytecode.

The factory's optional `team.version = 1` extension stores the second drone's position/cargo and two-element action/blocked counters. Missing extensions remain absent until the first team step so existing world digests and solo checkpoints stay valid. Chapter saves optionally add `team_code` and `execution: "team"`; the existing `code` remains Drone 1. Both programs, continuations, and world save together. Reloads and imports restore paused. Returning to solo mode preserves the parked drone; there is no offline advancement or shared server session.

## Recycling materials

Installed recycling adds residue, compost and fertilizer to both drones' cargo maps. Stock, outputs and growing supplies are shared; alternating pad priority and atomic transfers apply unchanged. The new machines advance once per combined tick. Returned products at the well enter shared care supplies; carried products stay with their drone, including when parked. The new Recycling autopilot example is solo; customize both controllers to divide bakery and recycling work. Original team starters do not clear the optional residue hopper. [Full recycling rules](RECYCLING.md).
