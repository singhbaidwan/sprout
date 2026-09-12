# Product requirements

## Brief and interpretation

Build a browser game in an initially empty repository where the player automates a farm with a drone using Python. Keep the project understandable and record requirements, implementation steps, and future work. The first release is a complete local single-player loop, not a hosted multiplayer service.

**Working title:** Sprout. **Audience:** curious programmers, beginners learning loops and conditions, and automation-game players. **Core promise:** write code, watch the drone carry it out, earn harvest income, improve the program, and unlock more of the farm.

## Core loop

1. Inspect the field and current mission.
2. Write or load a Python script using the drone API.
3. Run it and watch individual actions change the field.
4. Pause, step, stop, inspect errors, and edit the script.
5. Harvest crops for coins; finish missions and purchase unlocks.
6. Repeat with conditions, loops, and functions to automate more plots.

## First-release requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| F01 | Browser-based farm | A readable 6×6 field shows soil, crops, moisture, drone position, and tile inspection. |
| F02 | Python-driven drone | Scripts support variables, conditions, for/range, while, functions, returns, break, and continue. |
| F03 | Farming simulation | Tilling, planting, watering, growth, harvesting, movement, and waiting change deterministic state. |
| F04 | Economy and progression | Three crops, crop unlocks, an 8×8 expansion, and four sequential missions provide goals. |
| F05 | Playback controls | Run, pause/resume, single action stepping, stop, and playback speed work. |
| F06 | Useful feedback | Line-aware script errors, a bounded activity log, and live counters explain results. |
| F07 | Onboarding | A runnable starter, additional example scripts, and an in-game API guide make the first harvest easy. |
| F08 | Persistence | State, script, and speed save locally; reload restores valid progress; reset requires confirmation. |
| F09 | Accessible interface | Semantic controls, visible focus, keyboard editor support, reduced motion, and responsive layouts. |
| F10 | Reproducible project | One-command local launch, automated engine/interpreter/API tests, and maintained documentation. |

## Game rules

- Field coordinates start at `(0, 0)` in the northwest; x increases east, y increases south. Moving off an edge wraps around.
- The drone begins at `(0, 0)`. Three ripe wheat plots and 20 coins provide a quick start.
- Actions advance simulation ticks; wall-clock waiting does not grow crops. Pausing or stopping also stops farm time.
- Empty ground must be tilled before planting. Water allows growth for 24 ticks. Mature crops do not wilt.
- Wheat: seed 1, sale 5, growth 6 ticks, available initially.
- Carrot: seed 3, sale 12, growth 9 ticks, unlock 40 coins.
- Sunflower: seed 5, sale 20, growth 12 ticks, unlock 100 coins.
- Expansion: 150 coins, increases both dimensions from 6 to 8, retains existing crops and drone position.
- Wheat seeds remain affordable at zero coins via a free emergency wheat seed; no permanent bankruptcy state.
- Missions: harvest 3 crops (+20), plant 12 crops (+25), harvest 6 carrots (+60), earn 200 crop-sale coins (+100).
- Completed missions pay automatically once and remain complete. Crop-sale income excludes mission rewards.

## Boundaries and quality

- Python 3.10+ standard library backend; HTML, CSS, and JavaScript browser client; no install-time or runtime third-party dependency.
- Script evaluation must use an allowlisted AST interpreter, never `eval` or `exec`. No imports, attributes, file/network/process access, or unrestricted host objects.
- Bounded request size, source length, syntax-tree size/depth, operations, call depth, numeric/string/list sizes, actions, and output prevent ordinary accidental runaway scripts.
- The server is local development software bound to loopback. Public deployment needs a separate threat review, a production server, authentication/rate limits, and process isolation.
- Single-player saves are editable browser data, not an anti-cheat boundary. No accounts, multiplayer, cloud sync, idle/offline growth, packages, or unrestricted Python in version 1.

## Definition of done

The documented launch command serves the game; a first-time player can run an example, harvest, complete a mission, and purchase an unlock. Valid saved state survives reload. Script failures and stop retain only already-played changes. Automated tests and a real-browser pass validate primary interactions. Documentation describes implemented features and distinguishes remaining work.
