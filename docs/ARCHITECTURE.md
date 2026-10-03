# Architecture

## Overview

Sprout is a local Python application with a browser UI. It uses no third-party packages, network services, generated image assets, or build tooling.

```text
Browser                                  Python process (127.0.0.1)
──────────────────────────────────────   ──────────────────────────────────
index.html / style.css                   run.py → farm/server.py
app.js: editor, controls, local saves    GET /api/bootstrap → rules/examples
farm.js: responsive canvas world        POST /api/run → interpreter → Farm / Factory
      │                                 POST /api/validate → validated save
      └──── JSON request/response ────── POST /api/unlock → Farm.unlock
```

## File responsibilities

| Path | Responsibility |
| --- | --- |
| `run.py` | CLI arguments, loopback server startup, useful startup failure, clean shutdown. |
| `farm/engine.py` | Rules, state construction/validation, crop growth, actions, economy, missions, expansion. |
| `farm/common.py` | Shared actionable error and integer validation primitives. |
| `farm/cultivation.py` | Versioned optional care state, configuration, supplies, irrigation, growth modifiers, harvest effects, goals, and APIs. |
| `static/cultivation-ui.js` | Options, supply/goal dashboard, inspection text, and crop-care guide. |
| `farm/factory.py` | Breadworks catalog, inventories, recipes, routes, upgrades, missions, orders, and strict world validation. |
| `farm/recycling.py` | Optional residue, composter/mixer production, pause/resume and conserved-material validation. |
| `farm/layout.py` | Atomic movable-pad validation and sparse optional layout extension. |
| `static/layout-rules.js`, `static/layout-ui.js` | Preview validation, shortest movement distances, keyboard placement and layout guide. |
| `static/recycling-ui.js` | Configuration, new stock/status/goals, dynamic building catalog and recycling guide. |
| `farm/efficiency.py` | Optional bounded counters, pre-action baselines and strict measurement validation. |
| `farm/challenges.py` | Versioned snapshots, fixed budgets, outcome resolution and personal-score validation. |
| `static/challenges-ui.js` | Challenge lobby/progress, measurement presentation, record ranking and duplicate-record prevention. |
| `farm/world.py` | Explicit scenario selection and validation; classic and factory state versions remain distinct. |
| `farm/saves.py` | Portable envelopes, chapter/world matching, legacy migration. |
| `static/factory-ui.js` | Catalog-driven machine dashboard, order status, factory inspection and guide. |
| `farm/team.py` | Two-controller planning, shared-resource arbitration, one world tick, versioned team continuation. |
| `farm/continuous.py` | Compile validated syntax to bounded instructions; one-action scheduling and typed portable continuations. |
| `farm/interpreter.py` | Python AST validation, expression/statement interpretation, resource budgets, action frames, errors. |
| `farm/server.py` | Explicit static asset allowlist and JSON endpoints, request/origin/host checks. |
| `static/index.html` | Semantic game workbench, controls, dialogs, canvas, editor. |
| `static/style.css` | Responsive visual system and reduced-motion preferences. |
| `static/app.js` | API client, editor highlighting/indentation, playback state machine, saves, examples, guides. |
| `static/farm.js` | Original isometric geometry, deterministic scenery, crop/drone rendering, selection. |
| `examples/*.py` | Executable player scripts also supplied to the UI by bootstrap. |
| `tests/` | Engine, language, campaign, and real HTTP integration tests. |

## State and clock

State is a JSON-compatible object with `version`, `size`, `tick`, `coins`, `drone`, `tiles`, `unlocked`, `completed`, and `stats`. Tiles are row-major (`index = y * size + x`). Each tile stores `tilled`, `crop`, `growth`, and `water`.

An action validates its preconditions, applies its effect, advances the tick, grows all watered crops, decreases moisture, and checks sequential mission rewards. A failed action does not advance time or mutate state. Queries and `print` do not advance time. Mission rewards are distinct from lifetime crop-sale income.

`Farm` copies and validates provided state. `snapshot()` produces independent deep copies. Expansion remaps existing `(x, y)` coordinates into the wider row stride.

## Bounded script execution and playback

1. The browser sends current displayed state and editor text to `POST /api/run`.
2. Python validates state, parses and validates the entire syntax tree, and interprets it with explicit limits.
3. Each successful drone command produces a frame with its source line, action, message, resulting state, and mission events. Print frames contain output only.
4. A runtime failure returns previous frames plus a line-aware error. Unsupported syntax is rejected before any actions run.
5. The browser animates the returned frames at the selected speed. Only applied frames become the visible state and save.
6. Pause stops playback. Step applies one drone action (and any adjacent output). Stop discards remaining frames and pending errors. An aborted or stale response cannot later overwrite state.

This is a **bounded simulation followed by playback**, not a persistent Python process and not real-time streaming. Branches observe the simulated results of earlier commands in that run. Local calculations between actions are not visual debugger steps. Stopping during request preparation may leave the short bounded server calculation running, but its response is ignored and it changes no server-side farm state.

Every run begins a fresh variable/function environment while keeping farm state. Scripts have no variables that persist across runs. Editor and workshop changes are disabled during active playback. Browser speed affects animation delay only.

## Continuous execution

The optional Continuous mode uses `farm/continuous.py`. A compiler converts the validated allowlisted AST into explicit instructions, including jump targets, function entries, and for-loop records. The VM resumes expression/call/loop stacks until one action succeeds, the program finishes, or its work quota faults. `Farm.action()` remains the single shared world-clock boundary. Navigation stores remaining moves and yields after each tile.

Each request rebuilds instructions from source and validates the typed checkpoint; it never executes imported bytecode. Checkpoints bind source and world via digests, preserve variable aliases with bounded references, and contain no arbitrary host objects. No server session or secret is required. The browser commits world/continuation together, verifies the response revision, and ignores requests invalidated by Pause/Stop. A failed network request retries from the last acknowledged snapshot without duplicate transfers.

Continuous work is capped at 20,000 operations and 100 print messages **between actions**, retaining the source/value/call limits below. Continuations are limited to 48 KB, 2,500 expression values/encoded objects, and 256 active for loops. Reload and import restore paused. Full specification and compatibility rules: [CONTINUOUS.md](CONTINUOUS.md).

## Interpreter boundaries

There is no `exec`, `eval`, dynamic import, attribute traversal, or unrestricted host object in the player language. Calls resolve only to explicit game functions, bounded helpers, or interpreted player functions. Assignments only target names; list mutation, unpacking, slicing, imports, classes, lambdas, comprehensions, decorators, keyword arguments, annotations, and exceptions are unsupported.

| Resource | Limit per bounded run (continuous differences above) |
| --- | --- |
| Source | 16,000 characters |
| AST | 2,500 nodes, 60 levels |
| Interpreter operations | 20,000 |
| Drone actions | 400 |
| Print calls | 100, at most 2,000 characters each |
| Numbers | Finite, absolute value at most 1,000,000,000 |
| Sequence lengths | 1,000 items/characters |
| Nested lists/tuples | 1,000 total items, 8 levels |
| Function calls | At most 24 nested user function calls |

String formatting via `%` and exponentiation are unavailable. Collection arithmetic is checked before allocation and nested sizes are checked before values can be reused. `print` and `str` use bounded display formatting; long/deep collections are abbreviated.

This is a small game language, not a complete implementation of Python. In particular, simple scopes and bounded display/collection behavior should not be treated as a replacement for a normal Python tutorial or runtime. Language extensions must preserve the bounds and get failure-path tests.

## HTTP API

All POST requests require `Content-Type: application/json`. Run/upgrade/order requests have the original 100,000-byte limit. Portable save validation permits 1,000,000 bytes for campaign chapters, the isolated challenge trial and records; controller stepping retains 600,000 bytes for programs/checkpoints, including JSON escaping overhead. HTTP errors have `{ "error": "message" }`. Script errors are part of a successful `/api/run` response so earlier frames can still play.

`POST /api/layout` takes `{state, positions}` and returns `{state, message}`. It replaces the complete sparse machine-position map after validating every destination together. `{}` restores defaults. See [LAYOUTS.md](LAYOUTS.md) for placement constraints, order/trial restrictions and save compatibility.

| Endpoint | Input | Output |
| --- | --- | --- |
| `GET /api/bootstrap` | None | `{state, crops, missions, examples, chapters, cultivation}` |
| `POST /api/validate` | `{state}` | `{state}` rebuilt from known fields |
| `POST /api/run` | `{state, code}` | `{frames, error, actions, operations}` |
| `POST /api/controller/step` | `{state, code, checkpoint?}` | `{frames, state, checkpoint, revision, done, error, actions, operations}` |
| `POST /api/challenge/start` | `{id, drones}` | `{state, codes}` |
| `POST /api/efficiency/reset` | `{state}` | `{state, message}` |
| `POST /api/team/step` | `{state, codes: [source1, source2], checkpoint?}` | `{state, checkpoint, revision, done, error, frames, actions, operations, drones}` |
| `POST /api/unlock` | `{state, item}` | `{state, message}` |
| `POST /api/recycling` | `{state, enabled}` with a boolean | `{state, message}`; optional campaign module, no tick |
| `POST /api/settings` | `{state, settings}` with three booleans | `{state, message}`; change growing options without ticking |
| `POST /api/order` | `{state}` in factory chapter | `{state, message}`; start/retry a timed order |
| `POST /api/save/validate` | `{save}` | `{save}`; validate/migrate the portable chapter envelope |

The server accepts only local Host headers for its actual port and rejects mismatched Origin headers. Static routing is an explicit allowlist; it never exposes arbitrary project files or directory listings. Responses have a self-only content policy, no framing, no sniffing, and no-cache headers. No CORS access is granted.

## Persistence

The browser stores a version 2 `sprout-save` envelope under `sprout.save.v2`, with an active chapter and a map of chapter state, editor text, playback speed, optional execution mode, and optional versioned controller checkpoint. `farm/saves.py` migrates the original `sprout.save.v1` envelope into the classic chapter; the classic world schema stays at version 1, while Breadworks uses version 2 with `scenario: "factory"`. The envelope can contain one or both chapters, and its chapter key must match the validated world. `POST /api/save/validate` validates portable envelopes, rebuilding known fields. Imports validate before confirmation and back up the current envelope under `sprout.save.backup` before replacement; export produces a JSON download. The old v1 key is retained during migration. It saves after each displayed action, after upgrades, after edits (debounced), and on page exit. A reload validates state with Python before using it. Only displayed actions are restored. Bounded queues are discarded; continuous checkpoints restore paused and retain variables and control position.

Saves belong to the browser origin, so `localhost`, `127.0.0.1`, and different ports each have separate saves. Private browsing or clearing browser data can remove progress. Multiple tabs use last-write-wins behavior. There is no cloud sync, anti-cheat guarantee, or account recovery.

## Local-use scope and extension points

Python's standard-library server is suitable for this local prototype; it is explicitly not intended for production hosting. See the official [http.server documentation](https://docs.python.org/3/library/http.server.html). The interpreter uses Python's [AST library](https://docs.python.org/3/library/ast.html) for parsing, then evaluates only its own allowlist. Bounded execution is defense against ordinary runaway scripts; it is not a claim of hardened multi-tenant isolation.

For public hosting, introduce a production HTTP layer, isolated worker processes with OS resource limits, authentication, CSRF protections appropriate to the deployment, per-user request limits, durable state, and a security review. Keep engine rules separate from that infrastructure.

Add crops and missions in `engine.py`, update renderer visuals and workshop metadata, and extend tests and guides together. If save structure changes, increment its version and implement an explicit migration.

## Breadworks simulation boundary

`Factory` shares the existing crop rules, snapshot mechanism, and action clock with `Farm`. The base `advance()` increments tick/actions, applies irrigation pulses, grows crops with optional soil/fertilizer modifiers, reduces boost timers, invokes `advance_systems()` once, then checks care goals and the scenario's sequential missions. Factory systems advance the mill and oven, resolve the active order, advance enabled recycling machines once, resolve challenge outcomes and append events. One action therefore advances all systems exactly once; no extra ticking occurs for each machine.

Factory `harvest` overrides classic selling to add three wheat to cargo. Moves use bounded terrain instead of wrapping. Transfer actions check item, positive integer amount, location, available stock, and destination capacity before mutation. Inventories are simple fixed item maps. The source consumes items and destination receives them atomically; the subsequent machine phase may start a batch on newly delivered input.

Recipe inputs are removed at batch start. For the mill and oven, `remaining > 0` represents one reserved output worth of ingredients; the output slot cannot fill from any other source. Completion increments output and production statistics. Loading products can free a slot and start the next batch on that same action tick. Purchasing a speed upgrade changes future batch durations, preserving remaining ticks of any existing batch. Recycling recipes reserve two output slots, as described below.

The item-conservation test compares wheat-equivalent quantities across cargo, chest, machine input/output, active batches, and delivered products: 1 wheat = 1 unit, 1 flour = 2, 1 bread = 2. The total must equal starting chest wheat plus harvested yield in every frame of the example campaign. Coins and mission rewards are separate from these quantities.

`navigate_to()` computes a bounded breadth-first route over at most 64 tiles. Its route steps call the same interpreter action path as manual moves, retaining source lines, action/operation quotas, snapshots, and partial progress when the 400-action budget ends. Named destinations resolve from the Python catalog. Unsupported or blocked destinations fail before movement. Bounded mode retains whole-run playback; Continuous stores remaining route moves in its checkpoint.

Factory saves include cargo, chest, machine input/output/remaining, upgrades, additional production stats, six mission IDs, and order status/start tick/start delivered/best time/completed count. Known fields are rebuilt and bounds validated. Save validation is consistency checking for an editable local game, not server-authoritative anti-cheat.

The UI stores an active chapter plus per-chapter state/code/speed. Chapter changes and order starts are disabled during request preparation or playback. Stop invalidates request tokens; late responses cannot overwrite a reset or a newer operation. Reset affects only the active chapter. Full frame snapshots are retained for this small fixed map; the optional two-drone extension uses conflict resolution and one combined tick. Larger worlds still require profiling before changing transport formats.

## Optional cultivation extension

Both chapters carry `care.version = 1`: three independent settings, one care record per tile (nutrients/boost/fertilized), fertilizer/compost/tank supplies, pump state, installed sprinkler indices, care statistics, and completed independent goals. Missing extensions migrate explicitly to defaults with all rules disabled. Existing malformed extensions fail validation. `farm/common.py` holds validation primitives so the care system and base engine avoid cyclic imports.

The irrigation phase precedes crop growth on every sixth world tick. Sprinklers run in installation order, checking bounded 3×3 areas and spending one tank unit only when at least one covered plot needs moisture. Each target is capped at the moisture threshold before the growth/moisture phase. The crop-growth modifier returns 0 for depleted soil on odd ticks, otherwise 1 plus an active fertilizer boost. Boost timers decrease once per action only when the feature is enabled.

Harvest handlers calculate sale/yield bonuses before the care harvest hook clears treatment, depletes optional nutrients, and collects optional compost. Factory cargo-capacity checks use the actual 3-or-4 yield before mutation. Care supplies remain a separate bounded store. Enabled recycling introduces compost/fertilizer as cargo products; unloading them at the well exports them into that shared store. Existing care supplies cannot be loaded back into cargo. The default item-conservation tests still cover base factory production; additional tests cover fertilized yields and resource consumption.

Configurations are validated as exactly three booleans and applied without ticking. Browser request tokens protect settings changes from late responses, and controls are disabled during playback. Toggling off does not remove inventory or equipment. Crop removal always clears its treatment. Expansion remaps the care grid and sprinkler indices with the same coordinate-preservation rule as crops.

Shared examples query scenario and enabled features, illustrating independent systems without requiring imports or player access to host objects. Bounded-run limits and local-only hosting assumptions remain in effect; Continuous renews its work quota at each action as described above.


## Two-drone execution

`farm/team.py` subclasses the continuous VM to plan one action on each independent start-of-tick world view. The acting drone's position/cargo is projected into the existing API fields, so no player-visible host concurrency or new command namespace is needed. Action validation runs on isolated copies. A planning error returns the unchanged world for that tick.

A `TickFactory` defers `advance()`. Alternating drone priority applies valid commands against shared state, reserving non-movement work tiles. Losers restore the pre-step continuation and re-evaluate queries next tick. Movement may cross because the two drones use separate air lanes. Only after resolution does `Farm.advance()` grow crops, advance machines, and resolve missions/orders once. Successful command totals are counted separately from world ticks. Output from a blocked speculative step is discarded to avoid duplicated print messages.

The response carries one final world, labeled message frames and two continuation records; the browser commits them together and uses the existing request/revision guards. A combined digest binds both sources and the world, including finished controllers. Team continuations are at most 100 KB and preserve the per-controller limits. Versioned optional world/save extensions preserve old solo checkpoint digests; disabling team execution retains the second drone's inventory and program. Full schema and player-facing conflict rules: [DRONE_TEAMS.md](DRONE_TEAMS.md).


## Efficiency windows and isolated challenges

`Farm` exposes no-op action-context, recording and before-advance hooks. `Factory` captures cargo/tank/delivery baselines before a successful action and counts it once. The shared world phase records automatic water consumption and categorizes each machine exactly once after transfers. Team planners mutate isolated copies; their measurements are discarded. Committed actions update the shared counters, then one `Farm.advance()` measures one phase. Failed or contested actions do not increment successful-command counters.

Challenge goal resolution runs after machine/order processing in that phase. The bounded interpreter unwinds with an internal completion signal after emitting the terminal action frame; the resumable VM and team scheduler return `done` with no checkpoint. This leaves the ordinary language quotas intact and prevents further ticks after a terminal result. Fixed-count checks live at public execution entry points, so the team planner can continue using the same bounded VM.

Metrics attach lazily: validation preserves old worlds without the extension, avoiding changes to checkpoint digests before the next action. Trial rules/metrics are strictly validated with the factory world. `saves.py` validates saved games through one helper and keeps campaign chapters, trial and personal records separate. Browser saves route challenge state to `trial.game`; the campaign remains untouched. The record marker is outside the source/world digest and survives export/reload. Rules, wire fields, measurements and migration boundaries are specified in [CHALLENGES.md](CHALLENGES.md).

## Optional recycling extension

`farm/recycling.py` adds default well/composter/mixer catalog entries only to installed campaign worlds. `recycling.version = 1` and three new inventory keys are absent from untouched worlds; validation keeps them absent, preserving old world/controller bindings. First enablement adds zero-valued keys to both cargo bags and the chest, without altering time or care settings. Disabling retains the extension and pauses machine progress; dynamic entities and transfers remain available. Challenges reject the extension even when disabled.

Each enabled successful harvest places one residue in a 48-item hopper, with a capacity check before any harvest mutation. Soil depletion is unchanged, but the care hook suppresses its instant compost when recycling is enabled. The composter converts 2 residue to 2 compost in 6 ticks; the mixer converts 1 compost to 2 fertilizer in 4. Both reserve two output slots and have 12-item input / 8-item output buffers. Processing is in `Factory.advance_systems()`, never the team planning or per-drone commit phase. New output cannot move until the following action; inputs delivered this tick can start a batch in this phase.

Strict validation reconstructs bounded machine/inventory records and accounts for half-residue units across the hopper, all cargo/chest stock, input/output, ingredients reserved by active batches and cumulative returns to care supplies. Each residue/compost weighs 2, fertilizer 1; the total equals twice the harvested residue count. Export counters retain consumed crop-care material without mixing in starting or purchased supplies. See [RECYCLING.md](RECYCLING.md) for the schema and operational contract. No compiler commands, checkpoint version, public server boundary or transport threading were added.

## Workshop layout extension

`farm/layout.py` validates a complete sparse position map before atomic configuration. `Factory.entities()` resolves overrides against immutable catalog definitions; navigation, docking, stock queries and team planning all use that resolved catalog. Recipe timing still uses the original machine definitions and the single shared phase. Terrain and air-lane rules are unchanged.

The optional extension remains absent in old worlds, and validation retains present empty extensions to preserve checkpoint hashes. Configuration prunes defaults. Layout validates after installed recycling and before fixed challenge rules. The UI discards old continuations through Stop, previews with pure bounded BFS helpers, and applies through the existing request/revision guards. Non-simulation configuration never updates efficiency counters. [Exact schema and endpoint](LAYOUTS.md).
