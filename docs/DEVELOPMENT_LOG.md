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
