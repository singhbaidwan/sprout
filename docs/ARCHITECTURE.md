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
| `farm/world.py` | Explicit scenario selection and validation; classic and factory state versions remain distinct. |
| `farm/saves.py` | Portable envelopes, chapter/world matching, legacy migration. |
| `static/factory-ui.js` | Catalog-driven machine dashboard, order status, factory inspection and guide. |
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

All POST requests require `Content-Type: application/json`. Run/upgrade/order requests have the original 100,000-byte limit. Portable save validation and controller stepping permit 600,000 bytes for programs and checkpoints, including JSON escaping overhead. HTTP errors have `{ "error": "message" }`. Script errors are part of a successful `/api/run` response so earlier frames can still play.

| Endpoint | Input | Output |
| --- | --- | --- |
| `GET /api/bootstrap` | None | `{state, crops, missions, examples, chapters, cultivation}` |
| `POST /api/validate` | `{state}` | `{state}` rebuilt from known fields |
| `POST /api/run` | `{state, code}` | `{frames, error, actions, operations}` |
| `POST /api/controller/step` | `{state, code, checkpoint?}` | `{frames, state, checkpoint, revision, done, error, actions, operations}` |
| `POST /api/unlock` | `{state, item}` | `{state, message}` |
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

`Factory` shares the existing crop rules, snapshot mechanism, and action clock with `Farm`. The base `advance()` increments tick/actions, applies irrigation pulses, grows crops with optional soil/fertilizer modifiers, reduces boost timers, invokes `advance_systems()` once, then checks care goals and the scenario's sequential missions. Factory systems advance the mill and oven, resolve the active order, and append events. One action therefore advances all systems exactly once; no extra ticking occurs for each machine.

Factory `harvest` overrides classic selling to add three wheat to cargo. Moves use bounded terrain instead of wrapping. Transfer actions check item, positive integer amount, location, available stock, and destination capacity before mutation. Inventories are simple fixed item maps. The source consumes items and destination receives them atomically; the subsequent machine phase may start a batch on newly delivered input.

Recipe inputs are removed at batch start. `remaining > 0` represents one reserved output worth of ingredients; the output slot cannot fill from any other source. Completion increments output and production statistics. Loading products can free a slot and start the next batch on that same action tick. Purchasing a speed upgrade changes future batch durations, preserving remaining ticks of any existing batch.

The item-conservation test compares wheat-equivalent quantities across cargo, chest, machine input/output, active batches, and delivered products: 1 wheat = 1 unit, 1 flour = 2, 1 bread = 2. The total must equal starting chest wheat plus harvested yield in every frame of the example campaign. Coins and mission rewards are separate from these quantities.

`navigate_to()` computes a bounded breadth-first route over at most 64 tiles. Its route steps call the same interpreter action path as manual moves, retaining source lines, action/operation quotas, snapshots, and partial progress when the 400-action budget ends. Named destinations resolve from the Python catalog. Unsupported or blocked destinations fail before movement. Bounded mode retains whole-run playback; Continuous stores remaining route moves in its checkpoint.

Factory saves include cargo, chest, machine input/output/remaining, upgrades, additional production stats, six mission IDs, and order status/start tick/start delivered/best time/completed count. Known fields are rebuilt and bounds validated. Save validation is consistency checking for an editable local game, not server-authoritative anti-cheat.

The UI stores an active chapter plus per-chapter state/code/speed. Chapter changes and order starts are disabled during request preparation or playback. Stop invalidates request tokens; late responses cannot overwrite a reset or a newer operation. Reset affects only the active chapter. Full frame snapshots are retained for this small fixed map; multiple drones and larger worlds require extending the single-controller scheduler with conflict resolution and one combined tick, as described in the roadmap.

## Optional cultivation extension

Both chapters carry `care.version = 1`: three independent settings, one care record per tile (nutrients/boost/fertilized), fertilizer/compost/tank supplies, pump state, installed sprinkler indices, care statistics, and completed independent goals. Missing extensions migrate explicitly to defaults with all rules disabled. Existing malformed extensions fail validation. `farm/common.py` holds validation primitives so the care system and base engine avoid cyclic imports.

The irrigation phase precedes crop growth on every sixth world tick. Sprinklers run in installation order, checking bounded 3×3 areas and spending one tank unit only when at least one covered plot needs moisture. Each target is capped at the moisture threshold before the growth/moisture phase. The crop-growth modifier returns 0 for depleted soil on odd ticks, otherwise 1 plus an active fertilizer boost. Boost timers decrease once per action only when the feature is enabled.

Harvest handlers calculate sale/yield bonuses before the care harvest hook clears treatment, depletes optional nutrients, and collects optional compost. Factory cargo-capacity checks use the actual 3-or-4 yield before mutation. Care supplies are a separate bounded store, not cargo or machine ingredients. The default item-conservation tests still cover base factory production; additional tests cover fertilized yields and resource consumption.

Configurations are validated as exactly three booleans and applied without ticking. Browser request tokens protect settings changes from late responses, and controls are disabled during playback. Toggling off does not remove inventory or equipment. Crop removal always clears its treatment. Expansion remaps the care grid and sprinkler indices with the same coordinate-preservation rule as crops.

Shared examples query scenario and enabled features, illustrating independent systems without requiring imports or player access to host objects. Bounded-run limits and local-only hosting assumptions remain in effect; Continuous renews its work quota at each action as described above.
