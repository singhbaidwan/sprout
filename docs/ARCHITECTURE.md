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
| `farm/factory.py` | Breadworks catalog, inventories, recipes, routes, upgrades, missions, orders, and strict world validation. |
| `farm/world.py` | Explicit scenario selection and validation; classic and factory state versions remain distinct. |
| `farm/saves.py` | Portable envelopes, chapter/world matching, legacy migration. |
| `static/factory-ui.js` | Catalog-driven machine dashboard, order status, factory inspection and guide. |
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

## Script execution and playback

1. The browser sends current displayed state and editor text to `POST /api/run`.
2. Python validates state, parses and validates the entire syntax tree, and interprets it with explicit limits.
3. Each successful drone command produces a frame with its source line, action, message, resulting state, and mission events. Print frames contain output only.
4. A runtime failure returns previous frames plus a line-aware error. Unsupported syntax is rejected before any actions run.
5. The browser animates the returned frames at the selected speed. Only applied frames become the visible state and save.
6. Pause stops playback. Step applies one drone action (and any adjacent output). Stop discards remaining frames and pending errors. An aborted or stale response cannot later overwrite state.

This is a **bounded simulation followed by playback**, not a persistent Python process and not real-time streaming. Branches observe the simulated results of earlier commands in that run. Local calculations between actions are not visual debugger steps. Stopping during request preparation may leave the short bounded server calculation running, but its response is ignored and it changes no server-side farm state.

Every run begins a fresh variable/function environment while keeping farm state. Scripts have no variables that persist across runs. Editor and workshop changes are disabled during active playback. Browser speed affects animation delay only.

## Interpreter boundaries

There is no `exec`, `eval`, dynamic import, attribute traversal, or unrestricted host object in the player language. Calls resolve only to explicit game functions, bounded helpers, or interpreted player functions. Assignments only target names; list mutation, unpacking, slicing, imports, classes, lambdas, comprehensions, decorators, keyword arguments, annotations, and exceptions are unsupported.

| Resource | Limit per run |
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

All POST requests require `Content-Type: application/json`. Run/upgrade/order requests have the original 100,000-byte limit. Portable save validation permits 300,000 bytes for two maximum-length programs, including JSON escaping overhead. HTTP errors have `{ "error": "message" }`. Script errors are part of a successful `/api/run` response so earlier frames can still play.

| Endpoint | Input | Output |
| --- | --- | --- |
| `GET /api/bootstrap` | None | `{state, crops, missions, examples, chapters}` |
| `POST /api/validate` | `{state}` | `{state}` rebuilt from known fields |
| `POST /api/run` | `{state, code}` | `{frames, error, actions, operations}` |
| `POST /api/unlock` | `{state, item}` | `{state, message}` |
| `POST /api/order` | `{state}` in factory chapter | `{state, message}`; start/retry a timed order |
| `POST /api/save/validate` | `{save}` | `{save}`; validate/migrate the portable chapter envelope |

The server accepts only local Host headers for its actual port and rejects mismatched Origin headers. Static routing is an explicit allowlist; it never exposes arbitrary project files or directory listings. Responses have a self-only content policy, no framing, no sniffing, and no-cache headers. No CORS access is granted.

## Persistence

The browser stores a version 2 `sprout-save` envelope under `sprout.save.v2`, with an active chapter and a map of chapter state, editor text, and playback speed. `farm/saves.py` migrates the original `sprout.save.v1` envelope into the classic chapter; the classic world schema stays at version 1, while Breadworks uses version 2 with `scenario: "factory"`. The envelope can contain one or both chapters, and its chapter key must match the validated world. `POST /api/save/validate` validates portable envelopes, rebuilding known fields. Imports validate before confirmation and back up the current envelope under `sprout.save.backup` before replacement; export produces a JSON download. The old v1 key is retained during migration. It saves after each displayed action, after upgrades, after edits (debounced), and on page exit. A reload validates state with Python before using it. Only played actions are restored; queued actions are never resumed after a reload.

Saves belong to the browser origin, so `localhost`, `127.0.0.1`, and different ports each have separate saves. Private browsing or clearing browser data can remove progress. Multiple tabs use last-write-wins behavior. There is no cloud sync, anti-cheat guarantee, save migration beyond version 1, or account recovery.

## Local-use scope and extension points

Python's standard-library server is suitable for this local prototype; it is explicitly not intended for production hosting. See the official [http.server documentation](https://docs.python.org/3/library/http.server.html). The interpreter uses Python's [AST library](https://docs.python.org/3/library/ast.html) for parsing, then evaluates only its own allowlist. Bounded execution is defense against ordinary runaway scripts; it is not a claim of hardened multi-tenant isolation.

For public hosting, introduce a production HTTP layer, isolated worker processes with OS resource limits, authentication, CSRF protections appropriate to the deployment, per-user request limits, durable state, and a security review. Keep engine rules separate from that infrastructure.

Add crops and missions in `engine.py`, update renderer visuals and workshop metadata, and extend tests and guides together. If save structure changes, increment its version and implement an explicit migration.

## Breadworks simulation boundary

`Factory` shares the existing crop rules, snapshot mechanism, and action clock with `Farm`. The base `advance()` increments tick/actions, grows crops, invokes `advance_systems()` once, then checks the scenario's sequential missions. Factory systems advance the mill and oven, resolve the active order, and append events. One action therefore advances all systems exactly once; no extra ticking occurs for each machine.

Factory `harvest` overrides classic selling to add three wheat to cargo. Moves use bounded terrain instead of wrapping. Transfer actions check item, positive integer amount, location, available stock, and destination capacity before mutation. Inventories are simple fixed item maps. The source consumes items and destination receives them atomically; the subsequent machine phase may start a batch on newly delivered input.

Recipe inputs are removed at batch start. `remaining > 0` represents one reserved output worth of ingredients; the output slot cannot fill from any other source. Completion increments output and production statistics. Loading products can free a slot and start the next batch on that same action tick. Purchasing a speed upgrade changes future batch durations, preserving remaining ticks of any existing batch.

The item-conservation test compares wheat-equivalent quantities across cargo, chest, machine input/output, active batches, and delivered products: 1 wheat = 1 unit, 1 flour = 2, 1 bread = 2. The total must equal starting chest wheat plus harvested yield in every frame of the example campaign. Coins and mission rewards are separate from these quantities.

`navigate_to()` computes a bounded breadth-first route over at most 64 tiles. Its route steps call the same interpreter action path as manual moves, retaining source lines, action/operation quotas, snapshots, and partial progress when the 400-action budget ends. Named destinations resolve from the Python catalog. Unsupported or blocked destinations fail before movement. Each scenario retains the whole-run response/playback model.

Factory saves include cargo, chest, machine input/output/remaining, upgrades, additional production stats, six mission IDs, and order status/start tick/start delivered/best time/completed count. Known fields are rebuilt and bounds validated. Save validation is consistency checking for an editable local game, not server-authoritative anti-cheat.

The UI stores an active chapter plus per-chapter state/code/speed. Chapter changes and order starts are disabled during request preparation or playback. Stop invalidates request tokens; late responses cannot overwrite a reset or a newer operation. Reset affects only the active chapter. Full frame snapshots are retained for this small fixed map; continuous controllers, multiple drones, and larger worlds require the scheduler and checkpoint work in the roadmap.
