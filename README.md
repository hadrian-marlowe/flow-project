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
inside `simulations/`.

## Where things live

- `simulations/<name>/<name>.py` — one runnable simulation per folder. Settings you
  can change are at the top of each file. Start with `simulations/ball_no_air/`.
- `src/flow_project/` — shared engine code every simulation reuses: the physics
  (`projectile.py`), playback rules (`player.py`), and drawing (`animate.py`).
- `tests/` — pytest tests. `make test` runs them all without opening any windows.
- `docs/superpowers/` — design documents and build plans for each simulation.
