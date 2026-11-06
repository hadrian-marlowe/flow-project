# Project 1: Ball with no air — design

Date: 2026-11-06
Status: draft, waiting for approval
Mockup of the screen: `simulations/ball_no_air/mockup.html` (also at https://claude.ai/artifact/HwkoejK6XQsR2gvnvN1cbo)

## What this is and why

This is the first project in a series for the course "Physics + Python: Simulating
Fluid Flow". The long-term goal is to learn physics by building simulations with AI
as a partner. The series starts small: a ball thrown through empty space with gravity
and nothing else. No air, no drag, no spin.

The point of project 1 is to *see* the physics. The ball flies across the screen, and
the numbers next to it (sideways velocity, up/down velocity, speed, time) change as it
goes. The student can pause at chosen moments, read the numbers, change a setting, and
run it again to see exactly how that change affected the flight.

Later projects (not part of this one) will add air resistance and then move into fluid
flow. Project 1's code is the foundation they build on, so the simulation loop must be
the kind that can take extra forces later.

## Goals

1. An animation window showing the ball flying along its path, with a trail behind it.
2. Numbers that update every frame, displayed next to the ball: vx, vy, speed. A clock
   showing elapsed time. A side panel with position, velocities, max height, and range.
3. Arrows on the ball showing vx (sideways) and vy (up/down), so the student can see
   that vx stays constant while vy shrinks, passes through zero at the top, and grows
   downward.
4. Pause and resume. Step forward by a chosen time interval. Optionally auto-pause
   every interval. Each pause leaves a ghost marker on the path labelled with its time.
5. Settings the student will change live at the top of the file with comments:
   launch speed, launch angle, gravity, start height, time step size, pause interval.
6. The motion is computed by stepping forward in tiny time slices (a real simulation),
   not by plugging into the closed-form parabola formulas.
7. Tests prove the simulation is right by comparing it against the exact formulas.

## Non-goals

- No air resistance, drag, wind, or spin. Those are later projects.
- No GUI widgets (sliders, text boxes) inside the window. Settings are edited in the
  file. Keyboard controls are enough for pause/step.
- No saving videos or images.
- No 3D.

## Anti-goals (what would make this a failure even if it runs)

- The physics hidden inside library calls or buried in plotting code. The student must
  be able to point at the lines that do the physics.
- A simulation that only works for the default settings. Changing gravity or the angle
  must just work.
- An animation so fast the numbers can't be read.

## Constraints

- Python 3.9, numpy, matplotlib, scipy (already in `requirements.txt`). No new
  dependencies.
- Code lives in `src/flow_project/`, tests in `tests/`, run through `make test` and
  `make run`. See `CLAUDE.md` for the full project rules.
- The student is in high school and learning Python. Code should be plain and
  commented. Prefer simple loops over clever numpy tricks where it doesn't cost much.
- Every function gets tests in the same change.

## How it works (decided)

### The physics (the student's decisions)

- Gravity only. Acceleration is `(0, -g)` with g = 9.8 m/s² by default.
- Time stepping, not formulas. Each slice of time `dt`:
  1. velocity changes by acceleration × dt
  2. position changes by velocity × dt
- The simulation ends when the ball comes back down to the ground (y < 0), with the
  last point clipped to y = 0.

### The screen (the student's decisions, matching the mockup)

- Ball with a dotted trail. Blue arrow for vx, orange arrow for vy.
- Text labels riding next to the ball: `vx`, `vy`, `v` (speed).
- Clock in the top corner: `t = 1.25 s`, with a pause marker when paused.
- Side panel: time, x, y, vx, vy, speed, max height, range.
- Pause/play on the space bar. Step forward one interval on the right arrow key.
  Auto-pause every interval is a setting at the top of the file (on by default).
- Every pause leaves a small grey ghost circle on the path with its time underneath:
  a space-bar pause, an auto-pause, and a step forward all leave one. (Student's
  decision, 2026-11-06. The mockup originally skipped the space-bar case; it has been
  fixed to match.)

### Builder's calls (my choices, not the student's — flag if you disagree)

- **Integration method: plain Euler** (velocity first, then position using the *new*
  velocity, sometimes called semi-implicit Euler). It is the simplest loop a student
  can read, and it's what air resistance will plug into. It is not perfectly exact: the
  error shrinks as dt shrinks. The test will show that with a small dt (0.001 s) the
  simulation lands within a small tolerance of the exact formulas. A more accurate
  method (velocity Verlet) is a natural later upgrade and could be its own lesson.
- **Two time steps.** The physics step `DT` (default 0.001 s) is tiny for accuracy. The
  animation shows one frame every `FRAME_DT` (default 0.02 s of simulated time), and
  plays slower than real time (default half speed) so the numbers are readable.
  The simulation is run fully *before* the animation starts, storing arrays of
  t, x, y, vx, vy. The animation then just plays back the stored arrays. This keeps
  the physics loop and the drawing code completely separate.
- **Module layout.** The student wants one folder, `simulations/`, holding every
  simulation in the series. Each simulation gets a subfolder with the file you run,
  its mockup, and a short README. Shared engine code that later simulations reuse
  stays in `src/flow_project/`.
  - `simulations/ball_no_air/ball_no_air.py` — **the file the student runs and edits.**
    All settings at the top with comments (speed, angle, gravity, start height, DT,
    FRAME_DT, pause interval, auto-pause on/off, playback speed). Calls the engine
    below, then opens the animation.
  - `simulations/ball_no_air/mockup.html` and `README.md` — already there.
  - `src/flow_project/projectile.py` — the physics engine: `step()` does one time
    slice; `simulate()` runs the loop and returns the arrays; `exact_position()` and
    `exact_velocity()` hold the closed-form formulas, used by the tests and for the
    "max height" and "range" readouts. The physics lines are clearly commented.
  - `src/flow_project/animate.py` — all matplotlib code: drawing, labels, arrows,
    keyboard handling, ghost markers. Takes the arrays and the settings as arguments
    so a later simulation can reuse it.
  - `src/flow_project/main.py` — becomes a tiny launcher: `make run` runs the default
    simulation; `make run SIM=ball_no_air` picks one by folder name.
  - `tests/test_projectile.py` — physics tests. `tests/test_animate.py` — animation
    tests. `tests/test_ball_no_air.py` — checks the simulation file's settings produce
    a valid run.
- **Testing the drawing code (my call):** the pure helper functions in `animate.py`
  (next pause time, frame index for a time, label placement) get exact tests. The
  drawing functions themselves get "headless" smoke tests: build the figure with
  matplotlib's non-window backend (Agg), advance a few frames, and check the ball
  moved and the labels updated. No window ever opens during `make test`.
- **Axes auto-fit** to the flight: x from 0 to range × 1.1, y from 0 to max height
  × 1.25, equal aspect off (so a flat long throw still fills the window).
- The existing `math_utils.py` and its test stay as they are.

### Tests (must pass before done)

- After one `step()`, velocity and position change by exactly the expected amounts.
- `simulate()` with small dt matches `exact_position()` and `exact_velocity()` at
  several times within tolerance (say 1% of range).
- vx never changes during a flight.
- Range and max height from the simulation match the formulas within tolerance.
- The simulation stops at the ground: last y is 0 and no y is negative.
- Changing g, angle, speed, and start height all produce sensible results (e.g.
  higher g → shorter range; 45° gives the longest range on flat ground).
- Animation helpers: given a pause interval and current time, the next pause time is
  computed correctly; frame index for a given time is correct.

## Left to the builder

- Exact look of arrows, fonts, colours in matplotlib (follow the mockup's spirit).
- How to position the text labels so they stay readable near the window edges.
- Playback speed value, as long as it's a named setting at the top of the file.
- Whether the ghost markers are drawn as scatter points or circle patches.
