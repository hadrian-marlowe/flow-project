# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This project is coursework for "Physics + Python: Simulating Fluid Flow".

## Commands

All targets go through the Makefile and use the project virtualenv at `.venv/` (created on demand).

- `make setup` — create `.venv` and install `requirements.txt` (re-runs only when requirements.txt changes)
- `make test` — run the full test suite with pytest
- `make run` — run the main program (`src/flow_project/main.py`)
- `make clean` — remove the venv and caches

Run a single test file or test directly with the venv's pytest:

```
.venv/bin/pytest tests/test_math_utils.py
.venv/bin/pytest tests/test_math_utils.py::test_add
```

## Layout

- `simulations/<name>/<name>.py` — one runnable simulation per folder, settings at the top; imported as `simulations.<name>.<name>`. Shared engine code stays in `src/flow_project/`.
- `src/flow_project/` — application code. Modules are imported as `src.flow_project.<module>`; `pytest.ini` sets `pythonpath = .` so tests and the `-m` entry point share that import root.
- `tests/` — pytest tests, mirroring module names (`test_<module>.py`).
- Python 3.9 is the system interpreter used by `make setup`; keep code 3.9-compatible.

## Project Rules

### Tests

- Write tests at the same time as the code. Every new function or feature gets its tests in `tests/` in the same change. Never add code without tests.
- Run `make test` before saying any task is done. All tests must pass.
- When a test fails, find the root cause before changing anything.

### Git

- Never commit directly to `main`.
- Never use git worktrees, ever, even if a skill suggests it. Always work in this one project folder and switch branches with `git checkout`.
- All work happens on a feature branch named `feature/<short-name>`, created from `main`.
- Make small, frequent commits on the feature branch with clear messages.
- When a checkpoint is done, tests pass, and my teacher has approved it: squash-merge the feature branch into `main` with one summary commit, then delete the feature branch. Only merge when I say the checkpoint is approved.

### Workflow

- Use the Superpowers skills for all work:
  - `brainstorming` before designing any new feature
  - `writing-plans` and `test-driven-development` while building
  - `requesting-code-review` before every merge into `main`

### Communication

- I'm a high school student learning Python. Explain what you changed and why in plain language.
- Point out which lines contain the physics.
- Keep all settings I might want to change at the top of each file, with comments.
