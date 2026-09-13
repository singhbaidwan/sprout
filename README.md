# Sprout — program your farm

**Write Python. Fly your drone. Grow an automated farm.**

Sprout is a playable, single-player browser game with a Python simulation. Write a short program, watch your drone work, earn harvest income, and improve your routine. The project runs locally with **no third-party dependencies**.

**Status:** two playable chapters. Start with Home farm, then build a working wheat → flour → bread production line in **The Breadworks**. The [roadmap](docs/ROADMAP.md) separates implemented factory mechanics from future conveyors, power, and multiple drones.

## Quick start

Requirements: **Python 3.10+**, Git to clone the project, and a modern browser. No `pip install`, Node.js installation, or frontend build is required to play.

```sh
git clone https://github.com/singhbaidwan/sprout.git
cd sprout
python3 run.py
```

Open [http://localhost:8000](http://localhost:8000). Keep the terminal running while playing. Press **Ctrl+C** in the terminal to stop the server.

If you already have this project, run `python3 run.py` from its root directory. On Windows, `py run.py` also works when the Python launcher is installed.

If port 8000 is busy:

```sh
python3 run.py --port 8080
```

Then open [http://localhost:8080](http://localhost:8080).

## Your first harvest

Your drone starts at `(0, 0)` on a 6×6 farm with 20 coins and three ripe wheat plots. The editor already contains a runnable example. Click **Run code** to harvest the wheat, replant the row, water it, and complete the first mission.

An example of the player language:

```python
for plot in range(get_size()):
    if can_harvest():
        harvest()

    if get_crop() == None:
        till()
        plant("wheat")

    water()
    move("east")
```

Moving past an edge wraps around. Each successful drone action advances the farm by one tick. Watered crops grow during those ticks; simply waiting in the browser does not grow them.

## Try the factory chapter

Select **02 · The Breadworks** at the top of the game. Its starter program turns 8 wheat into 4 loaves, sells them at the depot, and completes the opening three missions. Each chapter keeps its own progress and program.

- Harvest wheat into limited drone cargo; transfer items through a storage chest, mill, oven, and delivery depot.
- Use `navigate_to()`, `load()`, `unload()`, inventory queries, and machine status to program logistics around obstacles.
- Diagnose full buffers and missing ingredients in a live production dashboard. Machines keep working during every drone action.
- Complete six factory missions, purchase three upgrades, and deliver timed orders to beat your personal record.
- Learn with four new examples: **First bread**, **Harvest & store**, **Farm to bakery**, and **Order runner**.

This chapter uses one drone and finite programs. There are no conveyors, machine placement, power grids, or continuously running controllers yet. See the [Breadworks guide](docs/PLAYER_GUIDE.md#the-breadworks--factory-chapter).

## Customize crop growing

Open **Growing options** and independently enable:

- **Fertilizer:** feed crops, buy supplies, speed up growth, and improve harvests.
- **Irrigation:** install sprinklers, manage a shared water tank, and program refill trips.
- **Soil health:** track nutrients, collect crop residue, and restore depleted ground with compost.

Use **Smart crop care** or **Sprinkler network** from the example menu. There are three additional growing goals per chapter. Options default off and can be changed between runs; switching them off keeps equipment, supplies, and progress. See the [crop-care rules and Python API](docs/CROP_CARE.md).

## Home farm and shared features

- Program a drone to move, till, plant, water, harvest, and wait.
- Use variables, conditions, loops, functions, and state queries to automate the farm.
- Grow wheat, carrots, and sunflowers; spend coins on crop unlocks and an 8×8 field.
- Complete four missions and continue experimenting after the campaign.
- Run, pause, resume, step through one action, stop, and change playback speed.
- Edit highlighted code with indentation support, line numbers, and line-specific errors.
- Load four example programs and consult the in-game Python API guide.
- Inspect plots visually or through a text table.
- Save farm progress, code, and speed automatically in your browser; export and import JSON backups.

**Keyboard:** Ctrl/Cmd + Enter runs or pauses; Tab indents; Shift + Tab unindents. The layout adapts to desktop and phone screens.

## How Python works here

Both the simulation and script interpreter are written in Python. Player programs use a **deliberately limited Python subset**, evaluated by an allowlisted AST interpreter. They are not arbitrary Python programs: imports, packages, attributes, file/network access, and several advanced language features are unavailable.

Each run allows up to **400 drone actions** and **20,000 interpreter operations**. Infinite loops, excessive output, and oversized values stop with an error. See the [full language and command reference](docs/PLAYER_GUIDE.md).

The server simulates a bounded run and returns action frames; the browser plays them back. Pause freezes playback, and Stop keeps only the actions already displayed. Variables reset on the next run, while farm progress persists.

## Saves and local hosting

Progress lives in browser storage on this device. Refreshing restores played actions and editor text, but does not resume queued actions. Reset requires an in-game confirmation.

Use the same URL consistently: `localhost`, `127.0.0.1`, and different ports have separate saves. Use **Export save** for a portable JSON copy and **Import save** to restore it. Imports are validated before confirmation and retain a device-local backup. Original version 1 saves migrate automatically. Browser data removal can erase progress. There are no accounts or cloud backups yet.

The server binds to loopback and is intended for local play. Publishing this repository does **not** deploy the game. GitHub Pages alone cannot run its Python API; public hosting requires a production server and isolated script execution. See [architecture and deployment boundaries](docs/ARCHITECTURE.md).

## Development and tests

Run from the project root:

```sh
python3 -m unittest discover -s tests -v
```

The 69 current tests cover both campaigns, conserved factory items, atomic transfers, obstacles, machine timing, delivery deadlines, save migration, upgrades, all eight combinations of growing options, irrigation/soil/fertilizer rules, language limits, and HTTP endpoints. Tests use temporary loopback sockets. The suite has been validated locally on Python 3.14. GitHub Actions now runs a Python 3.10–3.14 matrix plus JavaScript syntax checks; remote CI results are separate from local validation.

Optional JavaScript syntax checks, if Node.js is available (POSIX shell):

```sh
node --input-type=module --check < static/app.js
node --input-type=module --check < static/farm.js
node --input-type=module --check < static/factory-ui.js
node --input-type=module --check < static/cultivation-ui.js
```

There is no build step or hot reload. After changing browser files, reload the page. Restart the Python process after changing backend files.

```text
sprout/
├── run.py                  # Local server entry point
├── farm/
│   ├── engine.py           # State, crops, economy, missions, upgrades
│   ├── cultivation.py      # Optional fertilizer, irrigation, soil care
│   ├── factory.py          # Cargo, recipes, routes, delivery goals
│   ├── world.py            # Scenario selection and validation
│   ├── saves.py            # Portable envelopes and legacy migration
│   ├── interpreter.py      # Bounded player-language execution
│   └── server.py           # Static assets and JSON API
├── static/                 # Browser interface and canvas renderer
├── examples/               # Runnable programs shared with the UI
├── tests/                  # Engine, interpreter, and HTTP tests
└── docs/                   # Requirements, design, guides, and work log
```

When changing game rules or the player API, update the examples, relevant tests, guide, and development log together. Save-format changes need an explicit migration plan.

Completed, verified features and milestones are committed and pushed to `origin` before starting the next milestone, as requested by the repository owner. See [project working agreements](AGENTS.md).

## Where the game could go next

The next substantial step is a resumable interpreter with one shared simulation clock. That enables continuous controllers, then cooperating drones and conveyors. Later goals can introduce power, research, crop byproducts, and production graphs. These remain proposed work; the current Breadworks chapter establishes the inventory and processing rules they will need.

Read the [roadmap](docs/ROADMAP.md) for completion criteria and the scheduling/save design.

## Documentation

| Document | Contents |
| --- | --- |
| [Requirements](docs/REQUIREMENTS.md) | Scope, game rules, and acceptance criteria |
| [Player guide](docs/PLAYER_GUIDE.md) | Controls, examples, command API, and troubleshooting |
| [Crop care](docs/CROP_CARE.md) | Configurable systems, supplies, equipment, and automation API |
| [Architecture](docs/ARCHITECTURE.md) | Modules, state, execution, storage, and limits |
| [Roadmap](docs/ROADMAP.md) | Suggested improvements and programmable factory concept |
| [Development log](docs/DEVELOPMENT_LOG.md) | Completed work, decisions, validation, and next steps |
