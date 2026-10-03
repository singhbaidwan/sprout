# Development log

## 2026-09-13 — initial build

### Requested outcome

Create a Python-programmable farm/drone browser game from an empty repository and preserve requirements and performed steps in documentation.

### Decisions

1. Treat “playable using Python” as writing Python scripts to control the drone, with the simulation itself also written in Python.
2. Deliver a local Python project with no dependencies; defer public hosting and accounts.
3. Use a deterministic action clock, finite script execution, and animated browser playback so pause/step/stop are predictable.
4. Interpret a documented Python subset instead of executing player text as host Python.
5. Store single-player progress in the browser and validate restored state on the backend.
6. Use an original canvas-rendered farm and a light green coding workbench; no external fonts or image assets.

### Work sequence

- [x] Inspect the empty workspace and available Python/Node runtimes; check applicable repository instructions.
- [x] Define scope, progression, game rules, acceptance criteria, and architecture direction.
- [x] Implement deterministic farm engine, save validation, missions, and unlocks.
- [x] Implement bounded Python interpreter and local HTTP API.
- [x] Implement farm renderer, editor, playback, guides, examples, and save/reset flows.
- [x] Write meaningful engine, interpreter, and HTTP integration tests.
- [x] Verify in a real browser and fix discovered issues.
- [x] Complete player/API reference, architecture, launch instructions, and validation record.

This checklist will be updated during delivery. Future changes should add a dated entry describing the request, decisions, modified behavior, verification, and outstanding work.

### Implemented behavior

- Original isometric canvas farm with soil, moisture, crop growth stages, animated drone/propellers, action particles, scenery, coordinate markers, and tile inspection.
- Six drone commands, eight state queries, interpreted Python loops/conditions/functions, explicit language limits, line-aware errors, and bounded activity output.
- Editor with syntax colors, line numbers, current/error line markers, indentation, keyboard shortcuts, and four example programs shared with the automated tests.
- Run/pause/resume, single-action stepping, stop, and four playback speeds. Displayed state is the save boundary; queued future actions are discarded on stop/reload.
- Three crops, two crop unlock purchases, a field expansion, four sequential missions, and free emergency wheat seeds to avoid bankruptcy dead ends.
- Local saves for state, code, and speed; server validation on reload; reset confirmation; recovery notices for storage/connection problems.
- In-game learning/API/crop guides, a text inspection table, native buttons/dialogs, responsive workbench, and reduced-motion support.

### Validation record

Runtime used: Python 3.14.0 and Node 20.10.0 on macOS. Python 3.10+ is the compatibility target; other Python versions have not yet been tested.

`python3 -m unittest discover -s tests -v` — **27 tests passed**. Coverage includes:

- Initial state independence, save validation, soil/water/growth rules, crop permanence, movement wrapping, invalid-action atomicity, and bankruptcy recovery.
- Mission reward uniqueness, crop unlock costs, and expansion preserving coordinate mapping.
- The real starter script's expected 49 coins / 3 harvests / 6 plants; all example scripts together completing all missions and buying all unlocks; an expanded-field maintenance cycle.
- Functions, conditions, loops, helpers, queries, source line errors, partial progress, unsupported syntax, blocked host access, recursion/infinite loops, action budget, output bounds, and aggregate collection bounds.
- Real HTTP startup, bootstrap/assets, script run, state validation, unlocks, wrong content type, oversized bodies, origin/host restrictions, and project-file exposure prevention.

The first integration-test attempt could not bind a loopback socket inside the tool sandbox. The same tests passed with approved local-network execution. This was an environment restriction, not a failing game assertion.

`node --input-type=module --check < static/app.js` and the equivalent check for `static/farm.js` — passed.

Real-browser checks in the Codex browser:

| Check | Observed result |
| --- | --- |
| Initial load | Farm, canvas, editor, examples, and controls loaded; no browser errors. |
| Single step | Exactly one harvest: 25 coins, one harvest, one tick; program remained paused. |
| Resume starter at 8× | Completed at 49 coins, 3 harvests, 27 ticks; mission advanced to planting. |
| Unlock carrots | Balance became 9; carrot card showed Unlocked. |
| Stop after one action | A three-action program stopped after its first move at tick 28; other actions did not apply. |
| Reload | Coins, missions, unlocked crop, coordinates, tick, speed, and editor were restored. |
| Runtime error | `move("east")` followed by planting on grass retained the move and reported an error on line 2. |
| Mobile layout | 390×844 viewport request; effective content/client width both 375 CSS px, without horizontal overflow. Farm and editor visually inspected. |
| Mobile controls | Loaded full-field example, stepped one action, stopped, and opened the Python API guide. |

### Improvements from verification

- Moved playback controls above the editor so the main action is visible without scrolling through code.
- Improved syntax contrast and added editor length limits matching the backend.
- Added a New farm footer control so reset remains reachable on mobile.
- Updated tutorial tips as missions progress instead of repeating the initial-harvest advice.
- Preserved existing saves on a transport failure during restoration rather than overwriting them with a fresh farm.
- Bounded aggregate nested collection sizes, not just outer lengths; handled invalid control-flow contexts without server errors.
- Corrected the isometric north indicator to match decreasing y.

### Delivery and known limits

The completed first release runs with `python3 run.py`. A local development server is left running for the handoff. Browser QA used the `127.0.0.1` origin; a separate `localhost` origin provides a clean initial farm for playing. These origins have separate browser saves.

This is a local single-player game and a bounded Python subset. Public deployment, arbitrary CPython/package execution, cloud saves, save migrations, user accounts, multiplayer, and a persistent debugger are outside this release. Browser QA covers the primary flows on the available browser; cross-browser, 200% text zoom, and assistive-technology audits remain future work. The reset confirmation is implemented; browser QA opens/cancels it rather than deleting existing test progress.

### Suggested next steps (not implemented)

1. Gather play feedback on mission difficulty, crop balance, and editor readability.
2. Add portable save export/import with versioned migrations and tests.
3. Expand the mission campaign with distinct automation puzzles and optional efficiency goals.
4. Consider obstacles, tools, or multiple drones only after the current action model is proven fun.
5. Add cross-browser and automated browser regression coverage; audit keyboard/screen-reader behavior and text zoom.
6. If full Python or public hosting is required, first design isolated execution workers and durable per-player state rather than exposing this local server.

## 2026-09-13 — Git setup, README, and factory direction

### Request

Initialize Git, prepare a repository README, connect `https://github.com/singhbaidwan/sprout.git`, use `main`, push the project, and assess a Factorio-style direction centered on programming.

### Completed preparation

- Confirmed the project directory had no Git repository and checked the existing Git author configuration.
- Initialized Git, named the branch `main`, and configured the supplied URL as `origin`.
- Checked GitHub's advertised HEAD/main refs before publishing; neither contained an existing commit.
- Expanded the README with cloning/launch instructions, a playable Python example, current features, save behavior, language limits, architecture, tests, and links to the project documentation.
- Extended `.gitignore` for local environments, secret configuration files, and test outputs.
- Reviewed the current engine/interpreter/server and wrote [ROADMAP.md](ROADMAP.md) with prioritized improvements and a concrete factory design.

### Design conclusion

Keep the farming identity and add a separate factory scenario. Begin with inventory and the chain wheat → flour → bread → deliveries. Follow with resumable controllers and a shared world tick, then conveyors, multiple drones, power, and research. The current whole-run interpreter, per-action crop clock, immediate harvest sales, and full-state frames are the main systems to evolve. Factory APIs in the roadmap are illustrative and not implemented.

### Publication and validation

- Published the complete 25-file project to `origin/main` with initial commit `3007af7` (`first commit`). The push created the remote `main` branch and configured upstream tracking.
- Re-ran all 27 Python tests successfully before publication. Both JavaScript module syntax checks and the staged whitespace check passed.
- No gameplay implementation changes were made in this request.

### Follow-up instruction

The owner requested that the complete current project be pushed first and that future completed features/milestones also be committed and pushed. This standing workflow is recorded in the root `AGENTS.md`. The initial commit includes the playable game, tests, README, and design documentation, rather than only a placeholder README.

## 2026-09-13 — portable save foundation

Requested: expand the approved farm/factory direction with more gameplay. The first milestone prepares backward-compatible saves before adding a separate factory chapter.

- Added a strict version 2 portable envelope and migration from the original version 1 browser save, retaining the old storage key.
- Added JSON export, validated import with review/confirmation, and a device-local backup before replacement.
- Added save validation HTTP endpoint and migration, rejection, independence, and endpoint tests.
- Added GitHub Actions for Python 3.10–3.14 and JavaScript module syntax checks. Local validation uses Python 3.14; CI execution remains remotely observable.
- Validation: 31 Python tests passed; JS syntax and whitespace checks passed. Browser import restored a legacy fixture with 73 coins, its program, and speed; reload retained them. An invalid version was rejected without changing the current game. The embedded browser did not expose a download event for the export action, so download completion was not verified there.
- Next authorized milestone: a separate Breadworks chapter with cargo, storage, a mill, an oven, delivery missions, and bounded Python logistics. Continuous controllers, conveyors, and multiple drones remain later proposals.

## 2026-09-13 — Breadworks production chapter

### Completed work and decisions

- Kept Home farm intact and added a separate saved Breadworks chapter on a fixed 8×8 map with 24 growing plots, three obstacles, and chest/mill/oven/depot pads.
- Added typed cargo and shared chest storage; factory harvest yields items instead of coins. Transfers validate location, amounts, available stock, and capacity before any mutation.
- Added deterministic wheat → flour → bread processing, input/output buffers, in-flight batches, three upgrades, six sequential missions, and optional repeatable delivery orders.
- Extended the bounded interpreter with named navigation, transfer commands, inventory/capacity/status queries, and delivery/tick counters. Navigation expands into ordinary visible actions, preserving the 400-action limit and source lines.
- Added four factory examples, a live production dashboard, canvas buildings/labels, chapter-aware guides and inspection, and independent state/program/speed persistence.
- Preserved classic world version 1 and introduced explicitly identified factory world version 2 inside the portable envelope. Larger save validation bodies accommodate two maximum-length escaped programs; ordinary run requests keep their original limit.
- Updated requirements, README, player guide, architecture, and roadmap to distinguish delivered behavior from future continuous controllers and logistics.

### Verification

- **50 tests passed** on Python 3.14: original farming/interpreter/API tests plus factory gameplay, per-frame item conservation, atomic failures, batch save/upgrade behavior, shared clock, navigation/budgets, order deadlines/retries, complete campaign, and two-chapter saves.
- JavaScript syntax checks and `git diff --check` passed.
- In-browser First bread completed with 127 coins, 4 delivered bread, 60 ticks, and three missions completed.
- Bought larger cargo, ran field tending, hit the chest capacity safely, and ran an order to completion in **148 ticks**. The run finished with 25 lifetime delivered bread and a saved personal record.
- Switching to Home farm restored its separate 73-coin test fixture and original program. Switching back kept factory state. A navigation Step applied exactly one tile at tick 560; Stop and reload retained that tick and machine progress.
- Verified factory API guide, desktop canvas/workbench, and phone-size production/order controls. Mobile content/client widths both measured 431 CSS pixels with no horizontal overflow. No browser warning/error logs were reported in the checked session.
- Fixed facility labels being overpainted by foreground tiles; labels now render after the ground layer. Moved current mission above the production panel for earlier visibility.

### Follow-up requested during implementation

The owner supplied The Farmer Was Replaced as a reference and explicitly requested optional, configurable fertilizer, irrigation, and other crop-growing automation. Reviewed the [developer's Steam description](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/), which describes Python-like drone programming, resource-funded technology, and continuous progression. Next authorized milestone: individually toggleable crop-care systems with automation APIs and save compatibility. These are not part of this factory commit yet.

## 2026-09-13 — configurable crop-growing systems

### Request and scope

The owner asked to deepen crop-growing automation after reviewing The Farmer Was Replaced, explicitly requesting fertilizer, irrigation, related growing tasks, and options players can turn on or off. Published the preceding Breadworks milestone as `86c9a09` before starting this work.

Reviewed the game's official Steam description. Its stated progression through programming concepts and resource-funded technology informed Sprout's modular direction. Exact mechanics, quantities, API names, and toggle behavior in this milestone are Sprout's own design, documented in [CROP_CARE.md](CROP_CARE.md).

### Implemented work

- Added independent **Fertilizer**, **Irrigation**, and **Soil health** switches in both chapters. Changes apply between runs without consuming time, resetting progress, or granting replacement supplies.
- Added a versioned `care` world extension with soil records, treatment/boost flags, supplies, pump state, sprinkler locations, statistics, and three optional growing goals. Old saves migrate with every option disabled.
- Added consumable fertilizer, purchases at the (0,0) supply well, six-tick growth boosts, nutrient restoration, and chapter-specific harvest bonuses. Factory capacity checks use actual harvest yield before mutation.
- Added placeable 3×3 sprinklers, a shared 60-water tank, deterministic six-tick watering pulses, manual-water consumption, well refills, and programmable pump control.
- Added per-crop nutrient depletion, slower growth on poor soil, compost from harvested residue, and compost application. Disabling soil rules preserves soil records.
- Added six bounded actions and seven sensors. Shared validation primitives live in `farm/common.py`; crop-care systems stay separate from factory processing.
- Added **Smart crop care** and **Sprinkler network** examples to both chapter menus, settings/supply/goal UI, soil/treatment inspection, sprinkler rendering, and a Growing systems guide.
- Updated requirements, architecture, player guide, README, roadmap, and the standalone crop-care reference. Existing simple examples remain available; the UI points players to supply-aware scripts when optional systems are on.

### Verification

- **69 Python tests passed**, including HTTP settings validation. New tests cover old-world migration, all eight option combinations in both chapters, strict settings, failed actions without mutations, fertilizer consumption and bonuses, depleted-soil timing, compost recovery, irrigation overlap/tank/pump/refill behavior, factory shared clock, save suspension, and expansion remapping.
- Original classic and factory campaigns still pass with options off. Existing interpreter limits and loopback-only hosting are retained.
- All four JavaScript modules passed syntax checks; whitespace checks passed.
- Browser: enabled all three systems on the classic 73-coin test fixture and ran Smart crop care. It completed 32 actions with 106 coins, 3 harvests, 6 fertilizer applications, 3 compost collected, 2 sprinklers, and 47/60 tank water.
- Disabled Irrigation, switched to Breadworks (which retained its own disabled options), switched back, and reloaded. Classic retained two enabled systems, equipment, supplies, program, and tick 32.
- Inspected desktop and mobile option layouts, field visuals, and supply/goal controls. Mobile content/client widths both measured 431 CSS pixels; no horizontal overflow. Browser logs reported no warnings/errors in the checked session.

### Remaining work

The game still uses finite single-drone programs and fixed factory buildings. Continuous controllers, conveyors, additional industrial recipes, weather, pests, and disease modules remain future work. Crop-care options can be changed between runs; Stop first if a program is running. Remote CI status and embedded-browser download completion were not verified in this milestone; local tests and save validation were verified as above.

## 2026-09-20 — continuous automation and portable checkpoints

### Request and scope

The owner asked to continue with the next milestone. Selected Roadmap Stage 3 after inspecting the clean published `main` branch at `5f34f0c`. This delivers continuous single-drone operation in both existing chapters. Multiple drones, conveyors, and construction remain Stage 4 proposals.

### Implementation and decisions

- Added `farm/continuous.py`: a compiler and resumable instruction interpreter using the existing language allowlist, game API, validation, value limits, and error model. Explicit expression values, call frames, loop records, and remaining navigation moves preserve exact program position after an action.
- Added one-action `POST /api/controller/step`. The existing `Farm.action()` clock advances crops, care systems, machines, and order deadlines once. Computation does not tick. Each request has fresh 20,000-operation and 100-output budgets; bounded runs retain their original 400-action cap.
- Added typed version 1 checkpoints, bounded to 48 KB, with 24 user-call depth, 2,500 value/object bounds, and 256 loop records. Bounded references preserve aliases without allowing cyclic/forward references. Source and world digests reject mismatched pairs. Bytecode is always regenerated from validated source.
- Kept the server stateless. Identical retries are deterministic; no farm changes happen in a hidden server session. Browser request tokens and expected revisions prevent late responses from overwriting paused/stopped/reset state. Multi-tab storage remains last-write-wins.
- Added a per-chapter Run mode selector, continuous Run/Pause/Resume/Step/Stop behavior, one outstanding request at a time, and atomic world/checkpoint saves. Pause/Stop discard in-flight unacknowledged results. Stop clears the controller while retaining farm progress; edit/settings/workshop/chapter controls stay locked while it is active.
- Extended the version 2 save envelope with optional execution mode and checkpoint fields. Existing saves default to bounded mode. Reloads/imports restore controllers paused, including nested functions and routes. Checkpoints need no process-local session or key, so server restarts and cross-device saves work.
- Increased save/controller request limits to 600,000 bytes and file imports to 590 KB; export uses compact JSON. Other API request limits remain 100,000 bytes.
- Added Continuous autopilot examples for Home farm and Breadworks, including all optional growing systems. A loop sustains farming, supply maintenance, production, and delivery. Loading the example automatically selects Continuous mode.
- Added the in-game Continuous guide and `docs/CONTINUOUS.md`; updated requirements, architecture, README, player guide, and roadmap with implemented behavior and remaining multi-controller work.

### Verification

- **81 Python tests passed** locally on Python 3.14, including real loopback HTTP tests. The initial sandboxed baseline could not open sockets; the full suite was then run with the loopback permission required by the project agreements.
- Tests cover more than 400 actions, exact per-step tick counts, deterministic retries, parity with finite scripts, nested calls/loop control/expressions, alias preservation, partially completed routes, print/operation/recursion/memory limits, completed-world retention on errors, malformed checkpoints, source/world binding, save migration, and HTTP behavior.
- Both continuous examples ran for 650 actions in each of all eight growing-option combinations: 10,400 checkpointed actions across 16 scenarios. Farming continues and Breadworks delivers bread in every case.
- JavaScript module syntax and whitespace checks passed.
- Browser QA used the isolated `127.0.0.1:8001` test save. A bakery checkpoint at tick 564 reloaded paused mid-route; Step moved exactly one tile to tick 565. Continuous production increased deliveries from 25 to 45. Pause held tick 803, Step advanced to 804, and Stop unlocked editing while keeping that state.
- A computation-only infinite loop reported the operation limit without advancing tick 804. Loading a valid controller recovered; reload restored its tick-805 checkpoint paused.
- Imported a separately generated nested-function fixture at tick 1/x=1. Restore showed a paused controller; Step executed its saved next `wait()` at tick 2/x=1, proving the function did not restart.
- Reviewed the in-game guide and controls on the default 431px viewport (no horizontal overflow) and at a desktop viewport (1425px content/client width). Restored the temporary viewport override. No browser warning/error logs were observed in the checked session.

### Remaining work

Stage 4 can add placeable machines and bounded conveyors, then cooperative drones with reservations and conflict resolution. Today's scheduler is single-drone; it must not simply advance the whole world once per new drone. Full snapshots remain appropriate for the small map. There is no offline execution, shared server session, public hosting, or unrestricted Python. Remote CI execution and embedded-browser file-download completion are separate from the verified local suite and import flow.

This milestone is committed and pushed as one coherent change under the owner's standing Git preference; the final task response records the verified published commit.

## 2026-09-20 — missing helper and bounded activity log

- Inspected the reported Breadworks editor and reproduced the cause: its copied field loop called `store_cargo()` but omitted that example's function definition. The script also continued to harvest after a full-chest warning. Restored the complete helper and enclosing field routine so storage failure exits safely; no farm actions were run on the user's active order.
- Added an actionable missing-helper diagnostic to both interpreter modes. Updated Harvest & store to preserve the required fertilized harvest yield before navigating to the chest, and clarified that both helper definitions belong to the example.
- Fixed the activity log at 180px with its own vertical scrollbar, constrained wrapping and flex widths, keyboard focus, and a Latest button. New messages follow the bottom only when already near it, allowing players to read older output. The existing 150-row cap remains.
- Verification: full Python suite (82 tests), JavaScript syntax, and browser checks of helper restoration and log scrolling/long-message containment. This is a separate fix milestone before multiple-drone work.

## 2026-09-20 — optional two-drone team and gameplay direction

- Implemented a Breadworks-only Drone team (2) run mode, separate Python programs/variables/routes/cargo, numbered green/blue canvas drones, a program selector, per-drone status/action/blocked counters, and a one-click farmer/courier starter. Both programs can be inspected during playback; editing requires Stop.
- Added a bounded scheduler that plans from the starting world, resolves shared work in alternating priority, retries contested work from the previous continuation, and advances crops, machines, supplies, goals and deadlines once per combined tick. Program faults commit neither planned action for that tick. No unrestricted Python threads were introduced.
- Chose separate flight lanes: drones can cross or share a tile, while work pads and crop actions contend. This keeps the first fleet milestone playable; physical collision avoidance, construction and conveyors remain separate proposals. Team mode is immediately available and optional, with no upgrade cost. Returning to solo preserves the parked second drone and cargo.
- Added a validated optional versioned team state and a combined source/world-bound continuation. Existing world snapshots and solo checkpoint hashes remain unchanged until a team is enabled. Both programs save together and restore paused; the stateless endpoint preserves deterministic retries and the existing local-only HTTP boundary.
- Added regression coverage for one-clock growth/machines, shared harvests and supplies, rotating pad fairness, independent navigation, compile/runtime faults, completion, save binding, old saves, parked cargo, final-deadline orders, and HTTP resume. Starter runs cover all eight growing-option combinations for 500 shared ticks each, checking wheat-equivalent item conservation at every tick.
- Browser verification: two actions on the first shared tick; independent editor selection; paused reload recovery; sustained production to 141 delivered bread by tick 1,392 without console errors; Stop/solo/team preserved the courier's four carried loaves and program; an intentional Drone 2 missing-helper error left the world at tick 1,392 and selected the correct source. The log remained 180 pixels high, capped at 150 rows, with no horizontal/page overflow.
- Updated the README, requirements, architecture, player guide, continuous guide and roadmap. Added DRONE_TEAMS.md with exact implementation rules, and DESIGN_DIRECTION.md with official Factorio / The Farmer Was Replaced references, ranked proposals and a recommendation to prioritize efficiency feedback and reproducible contract scenarios before further production chains.
- Refreshed the user's local server/game; the existing farm remained at tick 124 with 67 coins and its repaired harvest script. No farm action was run in the user's save during diagnosis or refresh. Preview gameplay used a separate browser origin.
- Verification: full 93-test suite passed after implementation; expanded 11-test team suite passed after adding deadline and per-tick conservation assertions. Final full-suite result and publication are recorded in the milestone handoff. All JavaScript modules pass syntax checks and `git diff --check` is clean.
- Outstanding proposals: efficiency scenario scores, production graphs, conserved residue/fertilizer/fuel chains, buildable machines/conveyors, crop rotation, configurable forecasts, and fleets larger than two. These are documented recommendations, not implemented APIs.

## 2026-09-29 — resumed verification and publication

- Confirmed the pending two-drone milestone and documentation were intact after the session interruption; the helper/log fix was already published as `0e86ddc`.
- Used the bundled Git and Python 3.12 runtime because system Git required an Xcode license agreement and the installed Homebrew Python binary was incompatible with the current CPU. No system license or installation changes were made.
- The fresh full-suite run exposed a test-client race: the server correctly rejected an oversized request with HTTP 413 before its body finished sending, producing BrokenPipeError in the test harness. Updated the harness to read and verify the response after an early broken pipe; the focused HTTP suite passes.
- Restarted the local game with the working Python runtime. The existing browser save restored at tick 124, 67 coins, 15 carried wheat, and 116 ticks remaining on its active order, with the repaired `store_cargo()` helper present. No game action was taken on this save.
- Final verification passed: all 94 tests on Python 3.12.14 (36.1 seconds), all JavaScript module syntax checks, and whitespace/diff checks. The live restored game exposes team mode and the 180px log without horizontal overflow. The final handoff records the confirmed published commit.

## 2026-10-03 — efficiency dashboard and reproducible challenges

### Scope and decisions

Continued the recommended next milestone from the published two-drone release (`5a21b54`), starting from a clean `main`. Selected measurable optimization plus three replayable scenarios. Conserved byproduct recipes, construction, power and larger fleets remain proposals rather than part of this change.

### Implemented work

- Added optional version 1 Breadworks efficiency windows: successful commands, moves begun with empty cargo, waits, transfers, manual watering, all tank consumption, and per-machine working/input-starved/output-full ticks. Baselines are captured before the first successful action. Team planning copies do not contribute counters; committed drone commands count individually while the shared world phase counts once.
- Added a dashboard with deliveries per 100 ticks, water per loaf, empty travel, machine-time bars and text, and a bottleneck hint. Campaign measurements can restart between programs without advancing time. Old saves/checkpoint bindings remain unchanged until their next action or an explicit measurement reset. Classic has no new measurement extension.
- Added Bakery Rush (12 bread/180 ticks), Waterwise Harvest (12 bread/500 ticks/24 tank water), and Full Buffers (24 bread/240 ticks). Each has fixed starting inventory, layout, settings and equipment, and supports one or two drones. Ordinary care actions remain usable; refilling does not erase consumed water. The contract resolves after one shared phase and cleanly stops every execution mode on success/failure, including the exact last-tick success case.
- Added a separate trial session with its own programs, speed, mode and checkpoint. Starting a challenge preserves both campaigns. Retry resets the fixed farm and preserves edited programs; Return restores the campaign; View saved attempt reopens the retained trial. Reload/import restore active controllers paused. Settings, upgrades, orders, metric resets and wrong-count execution modes are rejected for trials.
- Added six personal-record groups, best-success ranking by ticks/water/empty moves, last and previous results, changes between consecutive successes, and resolved-attempt counts. A persisted envelope marker prevents duplicate records on reload. Records remain editable local data, not an anti-cheat boundary.
- Added three challenge starter files and two HTTP endpoints, retained bounded execution and local-only hosting, and expanded save validation to 1,000,000 request bytes / 990 KB imported files. Controller request limits stay at 600,000 bytes. Validated optional schema fields keep existing saves compatible.
- Updated README, requirements, architecture, player guide, roadmap and design direction; added [CHALLENGES.md](CHALLENGES.md) with exact rules, measurement definitions, schemas, limits and starter baselines. CI now includes the JavaScript record-persistence check.

### Verification

- **111 Python tests passed on Python 3.12.14 in 38.1 seconds**, including loopback HTTP integration tests. New tests cover all six starter completions, deterministic snapshots, action atomicity, pre-delivery baselines, shared manual/automatic water accounting, machine tick categories, old checkpoint bindings, fixed rules/counts, terminal states, exact deadlines, water-budget precedence/refill behavior, isolated portable trials, record bounds and recorded-result consistency.
- All five browser JavaScript modules pass syntax checks. The Node check verifies successful ranking, failed-attempt retention, previous-result comparison data, per-team record separation and duplicate suppression after serialized reload. Whitespace checks pass.
- The first full HTTP run found a client-side connection reset while uploading an already-rejected oversized body. The test now submits an oversized declared Content-Length with a short body, verifying the server's early HTTP 413 response without depending on platform-specific upload timing. Focused HTTP tests and the final full suite pass.
- Simulated starters completed: Rush solo/team in 143/149 ticks, Waterwise in 462/219 ticks (24 water each), Full Buffers in 117/111 ticks. These are baselines, not optimal strategies; the stocked-grain Rush demonstrates that adding a farmer does not necessarily shorten transport-bound work.
- Browser QA used the separate `127.0.0.1:8001` origin. Full Buffers reloaded its tick-1 controller paused, retried with the same code, completed bounded playback at tick 117, and retained exactly one record after reload. Return restored its campaign at tick 1393, 145 bread, and the original farmer program.
- Two-drone Waterwise executed two commands in one tick and used 2 water. Reload restored both controllers paused. Stop/Return/View saved attempt preserved the retained world. Its live run completed at tick 219 with 12 bread and exactly 24 water; the dashboard showed 438 commands across 219 shared ticks. No browser error/warning logs were observed.
- Responsive checks found equal content/client widths at the default narrow viewport (436 px) and desktop (1410 px). The temporary desktop override was reset. Preview screenshots and test logs are outside the repository.

### Remaining work and publication

Measurement totals and bars are implemented; time-series graphs, metric-query Python APIs, hosted rankings, new recipes, configurable weather and movable buildings are not. Future scenario rule changes need a versioned record migration. The next recommended milestone is a conserved crop-byproduct chain linking soil care with factory production. It needs its own recipe/balance design.

## 2026-10-03 — optional crop recycling and manufactured growing supplies

### Scope and decisions

Continued from the published efficiency/challenges milestone `bddfb64` on clean `main`. Chose one optional Breadworks chain: **residue → compost → fertilizer**, with a split between soil restoration and fertilizer production. Fixed buildings and the existing transport API keep this a bounded milestone. Construction, conveyors, power and fuel recipes remain proposals.

### Implemented work

- Added a separate Recycling option, independent of Fertilizer/Irrigation/Soil health. First enablement installs a version 1 extension without advancing time or changing old crops, care supplies, coins or bakery progress. Old snapshots and item maps remain unchanged until enabled. Classic and fixed trials reject configuration.
- Enabled harvests collect one residue in a 48-item well hopper rather than adding harvest cargo. Soil health still consumes nutrients, but instant compost is suppressed while recycling is on. Full hoppers block harvesting atomically. Turning off resumes the original easy compost rule and pauses industrial collection/production.
- Added fixed composter `(1,5)`: 2 residue → 2 compost / 6 ticks; mixer `(5,5)`: 1 compost → 2 fertilizer / 4 ticks. Both use 12-item input / 8-item output buffers and reserve two output slots before starting. Their phase advances once after committed actions, including in team mode. No automatic transport was introduced.
- Extended existing navigation, transfer, cargo/stock/capacity/status queries to the new pads and three new items. All six items share cargo/chest limits. Products unloaded at the well enter bounded shared growing supplies; existing purchased/returned care stock cannot be loaded back into the logistics line. Disabled machines retain stock and exact batch progress, while cleanup transfers remain available.
- Added strict conservation validation across the hopper, both cargo bags, chest, buffers, reserved active ingredients and cumulative returns. Residue/compost weigh two units, fertilizer one; total material must equal twice the collected residue. Later care consumption is represented by retained export counters. Present malformed extensions fail; absent extensions stay absent, preserving old solo/team controller hashes.
- Added live configuration, machine/stock/progress cards, lifetime totals, two return goals without coin rewards, an in-game guide and original canvas well/composter/mixer geometry. Adjusted the composter map label to avoid overlapping the nearby chest label. Team cargo text includes carried recycling products; canvas accessible text names installed buildings.
- Added a finite first-fertilizer demo and a Continuous bakery/recycler example. The autopilot reserves compost, manufactures fertilizer when that care option is on, refills irrigation and does not buy fertilizer. Original examples retain their original teaching scope; documentation explains that they need extra transport logic when recycling is enabled.
- Added [RECYCLING.md](RECYCLING.md); updated README, requirements, architecture, player/continuous/team/care/challenge guides, roadmap and design direction. Proposed buildable logistics is identified as the next scope decision.

### Verification

- Baseline: all 111 existing tests passed before adding recycling regressions. Final suite: **127 Python tests passed on Python 3.12.14 in 54.840 seconds**, including temporary loopback HTTP sockets. Added tests cover capacities and atomic failure, usable returned supplies, two-output reservations, pause/resume, full hopper, all care combinations, conserved frames, team contention/faults, old/new portable continuations and endpoint/trial restrictions. One new test initially selected a trailing print frame as a world frame; corrected the test to select the final state-bearing frame.
- Separate 1,800-tick playtests of all eight care combinations delivered **54–61 bread**, with no interpreter errors or conservation failures. Fertilizer-enabled variants returned **40–48 manufactured doses**. The committed regression test runs each variant for 1,000 ticks and validates material/state every step.
- Browser on isolated `127.0.0.1:8001`: enabling changed no time; finite demo completed in **52 actions**, returning one compost and two fertilizer. Loading the new autopilot selected Continuous. Step/reload restored a paused checkpoint at tick 53 with supplies intact. A five-tick active compost batch remained at five through three disabled world ticks, then finished after re-enable and five ticks.
- Browser autopilot with Soil health and Fertilizer enabled reached **tick 1,450 / 44 bread delivered / 30 residue collected / 30 compost and 36 fertilizer produced**. Both return goals completed. No warning/error console entries were recorded. The activity log stayed **180px**, capped at **150 rows**, without horizontal overflow. Responsive checks at 375px and 1280px viewports showed no page overflow; temporary viewport overrides were reset. Visual proof was saved outside the repository at `/tmp/sprout-recycling.jpg`.
- Started the updated server on port 8000 with the bundled working Python runtime. The original `localhost:8000` save loaded at **tick 124, 67 coins, 4 bread delivered, 15/16 wheat cargo, 4 chest wheat and 116 order ticks remaining**, with the repaired `store_cargo()` program intact. No action or recycling configuration was applied to that save. Preview gameplay used its separate origin.
- All browser JavaScript modules pass module syntax checks. JavaScript challenge record persistence/ranking checks pass. `git diff --check` is clean. System Git still requires the unaccepted Xcode license, so the bundled Git is used; no system settings were changed. Remote `main` matched baseline `bddfb64` before publication. Completed milestone publication follows [AGENTS.md](../AGENTS.md); the handoff records the verified pushed commit.
- Final review strengthened the contested-output test to give Drone 2 the collected compost, park it, and round-trip a solo checkpoint/save with its nonzero cargo. The focused test passed after that addition; no game rules changed.

### Remaining scope

Both growing uses can be disabled; then the autopilot accumulates compost in bounded supplies rather than consuming it forever. The guide explains when to enable a use, change storage/production code or pause recycling. Mill/oven utilization remains the efficiency dashboard scope; new machines have live buffers/status rather than new time-series graphs. The new recycler starter is solo, while all transport rules support two drones. Buildable machines/conveyors, additional recycling challenges, larger fleets, power, crop rotation and weather remain separate proposals.

This completed feature is committed and pushed as one milestone under the owner's standing preference. The handoff records the remotely verified commit; remote CI execution is separate from the local verification above.

## 2026-10-03 — player-controlled workshop layouts

### Scope and decisions

Continued from published recycling milestone `77157e0` on clean `main`. Selected one playable logistics milestone: free relocation of existing workshop machines between programs, with route-distance previews and a finite comparison program. Extra buildings, construction costs, conveyors, power and blueprint sharing remain separate proposals.

### Implemented work

- Added atomic whole-layout validation for mill/oven and installed composter/mixer. Chest/depot/well remain fixed. Growing plots, rocks, map edges and overlapping buildings are invalid. Uninstalled recycling pads stay reserved, so later enablement cannot overlap a relocated bakery. Installed paused recycling machines can still move.
- Added optional sparse `layout.version = 1` / `positions` to version 2 factory worlds. Absent old worlds stay absent; present empty extensions survive validation for digest compatibility. Configuration prunes defaults and restores the old schema on Default layout. Malformed extensions fail. Portable solo/team continuations retain the layout and in-flight route/batch state.
- Resolved every factory entity through saved positions, covering named navigation, docking, transfers, queries, team contention, canvas, stock-card coordinates and plot inspection. Recipes and the single shared simulation phase remain unchanged. Moves preserve the rest of the world exactly, including active batches, stock, both drones/cargo, care, coins and efficiency windows; they take no time.
- Added stateless `POST /api/layout` with a complete sparse map replacement, copied-state validation and bounded loopback-only transport. Active orders block apply; fixed challenges reject layout configuration and even empty extensions. Stop discards old checkpoint routes before editing. Existing request tokens protect against late replies.
- Added keyboard-accessible placement pads, canvas outline, current/preview shortest-route distances, compact/default presets, discard/apply controls and in-game guide. Layout rendering avoids rebuilding every tick; map labels choose collision-free offsets for close buildings. Keyboard placement restores focus after rebuilding the grid.
- Added Layout delivery test: four individual flour transfers followed by four bread deliveries. It checks empty bakery machines, eight chest wheat and cargo space before taking actions. Fresh defaults complete in 54 ticks; compact layout in 48. This is a same-program baseline rather than a universal throughput guarantee.
- Added [LAYOUTS.md](LAYOUTS.md) and updated README, requirements, architecture, player/recycling/continuous/team guides, roadmap and design direction. Added pure JavaScript preview tests to CI. No compiler command, interpreter limit or save-envelope version changed.

### Verification

- All 13 focused layout tests passed in 5.839 seconds. Final suite: **141 Python tests passed on Python 3.12.14 in 62.065 seconds**, including temporary loopback HTTP integration. Coverage includes atomic rejection/swaps, old/new checkpoint hashes, preserved batch/cargo state, moved-pad transfers, team contention with one world tick, order/trial restrictions, optional recycling and 700-tick solo/team/recycler runs with all three growing options enabled. Existing eight-option regressions remain in the full suite.
- Every browser module passes JavaScript syntax checks. Both Node suites pass: challenge record persistence/ranking and new layout previews, reserved pads, entity positions, non-mutated catalog and shortest distances. Whitespace checks pass.
- Browser QA used separate `127.0.0.1:8001` storage. Compact preview displayed bakery distances 3→1, 3→1, 4→8 and recycling 6→4, 4→1, 10→5. Crop/rock pads were disabled. Apply kept tick 1,450, 44 delivered bread, mill output 4, oven output 7 with four batch ticks remaining, mixer input/output 2/8, and care stock 4 compost/6 fertilizer. Reload retained all four custom pads.
- Keyboard Enter moved a preview pad and retained focus; discard restored saved coordinates without ticking. The guide opened correctly. After resetting only the QA campaign, Layout delivery test finished at tick 48 with four delivered bread and the expected log. A custom-layout two-drone step reached tick 49, reloaded paused, then resumed to tick 50. Default restoration and reapplying compact both kept tick 50.
- Mobile (375px) and desktop (1280px) checks found equal document content/client widths; placement grid internal widths also matched. Activity log remained 180px. No warning/error console entries were observed. Temporary viewport overrides were reset, the QA tab was closed, and proof saved outside the repository at `/tmp/sprout-layouts.jpg`.
- Restarted the identified local port-8000 server using the bundled working Python runtime. The existing localhost save reloaded at tick 124 / 67 coins / four bread / 15 of 16 cargo / four chest wheat with the complete repaired `store_cargo()` program. Its active order disabled layout apply; preview/discard did not take actions or change the saved layout. Original user tabs remain open.
- The system Git remains gated by its unaccepted Xcode license; bundled Git is used without modifying system settings. Remote main matched `77157e0` before publication. This verified milestone is committed and pushed under [AGENTS.md](../AGENTS.md); the final handoff records the remotely confirmed commit. Remote CI execution is separate from these local checks.

### Remaining scope

Layouts currently relocate one of each existing machine. Conveyors need conserved transport buffers and a defined once-per-world-tick movement phase; storage targets need observable policies rather than automatic hidden transfers. Additional machines need construction/balance/schema design. Challenge maps and records remain fixed. None of those proposals is added as a player API by this milestone.
