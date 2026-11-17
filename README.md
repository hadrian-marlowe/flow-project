# flow-project

Coursework for "Physics + Python: Simulating Fluid Flow". A series of physics
simulations, each building on the last, starting with a ball thrown through
empty space.

## Quick start

```
make setup      # create the virtualenv and install requirements (first time only)
make run        # run the default simulation (ball_no_air)
make test       # run all the tests
```

Run a specific simulation with `make run SIM=<name>`, where `<name>` is a folder
inside `simulations/final/`, or `SIM=prototypes/<name>` for a draft.

## Where things live

- `simulations/final/<name>/<name>.py` — the finished version of each simulation.
  Start with `simulations/final/ball_no_air/`, whose window has on-screen boxes and
  buttons for everything.
- `simulations/prototypes/` — rough drafts, frozen as a record of how each
  simulation got there. Run one with `make run SIM=prototypes/<name>`.
- `src/flow_project/` — shared engine code every simulation reuses: the physics
  (`projectile.py`), launch numbers (`launch.py`), playback (`player.py`),
  drawing (`animate.py`) and the window (`launch_window.py`).
- `tests/` — pytest tests. `make test` runs them all without opening any windows.
- `docs/superpowers/` — design documents and build plans for each simulation.
