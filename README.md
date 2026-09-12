# Sprout — program your farm

**Write Python. Fly your drone. Grow an automated farm.**

Sprout is a playable, single-player browser game with a Python simulation. Write a short program, watch your drone work, earn harvest income, and improve your routine. The project runs locally with **no third-party dependencies**.

**Status:** first playable version. A proposed direction toward programmable production chains is documented in the [roadmap](docs/ROADMAP.md); factory features are not implemented yet.

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

## What you can do today

- Program a drone to move, till, plant, water, harvest, and wait.
- Use variables, conditions, loops, functions, and state queries to automate the farm.
- Grow wheat, carrots, and sunflowers; spend coins on crop unlocks and an 8×8 field.
- Complete four missions and continue experimenting after the campaign.
- Run, pause, resume, step through one action, stop, and change playback speed.
- Edit highlighted code with indentation support, line numbers, and line-specific errors.
- Load four example programs and consult the in-game Python API guide.
- Inspect plots visually or through a text table.
- Save farm progress, code, and speed automatically in your browser.

**Keyboard:** Ctrl/Cmd + Enter runs or pauses; Tab indents; Shift + Tab unindents. The layout adapts to desktop and phone screens.

## How Python works here

Both the simulation and script interpreter are written in Python. Player programs use a **deliberately limited Python subset**, evaluated by an allowlisted AST interpreter. They are not arbitrary Python programs: imports, packages, attributes, file/network access, and several advanced language features are unavailable.

Each run allows up to **400 drone actions** and **20,000 interpreter operations**. Infinite loops, excessive output, and oversized values stop with an error. See the [full language and command reference](docs/PLAYER_GUIDE.md).

The server simulates a bounded run and returns action frames; the browser plays them back. Pause freezes playback, and Stop keeps only the actions already displayed. Variables reset on the next run, while farm progress persists.

## Saves and local hosting

Progress lives in browser storage on this device. Refreshing restores played actions and editor text, but does not resume queued actions. Reset requires an in-game confirmation.

Use the same URL consistently: `localhost`, `127.0.0.1`, and different ports have separate saves. Browser data removal can erase progress. There are no accounts or cloud backups yet.

The server binds to loopback and is intended for local play. Publishing this repository does **not** deploy the game. GitHub Pages alone cannot run its Python API; public hosting requires a production server and isolated script execution. See [architecture and deployment boundaries](docs/ARCHITECTURE.md).

## Development and tests

Run from the project root:

```sh
python3 -m unittest discover -s tests -v
```

The 27 current tests cover farm rules, save validation, campaign completion, upgrades, language behavior, execution limits, and HTTP endpoints. Tests use temporary loopback sockets. The suite has been validated on Python 3.14; the documented Python 3.10+ range still needs a CI compatibility matrix.

Optional JavaScript syntax checks, if Node.js is available (POSIX shell):

```sh
node --input-type=module --check < static/app.js
node --input-type=module --check < static/farm.js
```

There is no build step or hot reload. After changing browser files, reload the page. Restart the Python process after changing backend files.

```text
sprout/
├── run.py                  # Local server entry point
├── farm/
│   ├── engine.py           # State, crops, economy, missions, upgrades
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

The proposed next chapter is a **programmable farm and factory**: harvest wheat into storage, process it into flour, bake bread, and deliver orders. Python would control production priorities and drone logistics. Later chapters could add conveyors, power, research, and cooperating drones.

Recommended order: portable saves and CI → inventory and one production chain → resumable simulation → logistics and multiple drones. Preserve the existing farm campaign while introducing these mechanics in a separate factory scenario.

Read the [prioritized roadmap and factory design](docs/ROADMAP.md) for concrete code changes, example future commands, acceptance criteria, and tradeoffs.

## Documentation

| Document | Contents |
| --- | --- |
| [Requirements](docs/REQUIREMENTS.md) | Scope, game rules, and acceptance criteria |
| [Player guide](docs/PLAYER_GUIDE.md) | Controls, examples, command API, and troubleshooting |
| [Architecture](docs/ARCHITECTURE.md) | Modules, state, execution, storage, and limits |
| [Roadmap](docs/ROADMAP.md) | Suggested improvements and programmable factory concept |
| [Development log](docs/DEVELOPMENT_LOG.md) | Completed work, decisions, validation, and next steps |
