# Ball with no air, version 2: the two-path launch window — design

Date: 2026-11-16
Status: approved by the student in chat (2026-11-16); supersedes the window described in
`2026-11-06-ball-no-air-design.md`. The physics engine from that design stays.
Mockup of the new screen: https://claude.ai/artifact/PFvzpLJrxSAQ88QN645aFS
(the student asked that no mockup files be kept in the project; the link is the reference).

## Why a version 2

The first window put every setting in the Python file and auto-paused by default. The
student tried it and found it unusable for the way they learn: they want to type new
numbers into the screen, press Play, and watch, and they want the path equation in front
of them with their numbers plugged in. They also want to compare two throws at once.

Nothing changes about the physics or the series plan: time-slice simulation now, air
resistance next, fluid flow later.

## Goals

1. **Everything is set on screen.** Boxes for x0, y0, v0, θ, vx, vy per path, and g.
   No need to edit the file to run an experiment. Changes take effect on the next Play,
   never mid-flight.
2. **The path equation is on screen**, with the current numbers substituted in:

       r(t) = ( x0 + (v0 cos θ) t ) î + ( y0 + (v0 sin θ) t − ½ g t² ) ĵ

   Each number in it is clickable. Clicking highlights the matching box in the side panel
   and puts the cursor there. Small A / B buttons choose which path the equation shows.
3. **Linked velocity boxes.** v0 and θ describe the same arrow as vx and vy. Typing in
   either pair updates the other pair immediately (vx = v0 cos θ, vy = v0 sin θ;
   v0 = √(vx² + vy²), θ = atan2(vy, vx)). Typing vx with vy unchanged therefore changes θ.
   The student understands and accepts this (discussed 2026-11-16).
4. **Two paths at once.** Path A (blue) and Path B (orange), each with its own launch
   boxes, trail, ball, arrows and on-ball numbers. Shared: g, axes, playback. Both launch
   at t = 0 when Play is pressed. Path B has an on/off checkbox; A is always on.
5. **Play just plays.** Press Play (or space) and the flight runs to the end. Auto-pause is
   off by default; a checkbox plus an interval box turns it on. Space pauses and resumes.
   Right arrow steps forward one interval. A jump-to-t box lands on an exact time. A time
   slider under the plot scrubs to any moment.
6. **Every pause leaves a ghost marker** (grey hollow circle with the time underneath) on
   each visible path: space-bar pause, auto-pause, step, and jump all count. A "Clear
   markers" button wipes them. Dragging the slider does not add markers.
7. **Adjustable axes.** Boxes for x min, x max, y min, y max, plus an "Auto-fit axes"
   button that fills them from the current flights. Boxes start out auto-fitted.
8. **Simulation vs equation.** The ball's motion still comes from the time-slice engine.
   A small cross is drawn where the equation says the ball should be at the same time,
   and the readout shows the distance between the two (`sim − eq`). With no air they
   coincide; with air resistance later they will separate. (Student chose this
   "option B" on 2026-11-16.)
9. **Gravity presets** next to the g box: Earth 9.8, Moon 1.6, Mars 3.7, Jupiter 24.8.
10. **Show/hide toggles** for arrows and on-ball numbers, to calm a busy plot.
11. **Uncluttered layout**, exactly the four areas of the mockup:
    - equation banner across the top;
    - plot on the left, time slider under it, playback bar under that
      (Play/Pause, Step, "pause every __ s" checkbox+box, "jump to t" box+Go,
      speed 0.25×/0.5×/1×, Clear markers, clock);
    - side panel on the right with three labelled groups stacked: **Launch** (A and B as
      two columns, rows x0, y0, v0, θ, vx, vy, and a Path B on/off checkbox),
      **World & view** (g box + Earth/Moon/Mars/Jupiter buttons, x axis min/max,
      y axis min/max, Auto-fit, show toggles), **Readout** (one monospace table, columns
      A and B, rows x, y, vx, vy, v, range, max height, flight time, sim − eq).
12. `make test` still passes without opening any window, and `make run` opens this window.

## Non-goals

- No air resistance yet (next project). No wind, spin, bounce.
- No saving images or videos. No more than two paths.
- No typing directly inside the equation; clicking a number sends you to its box.
- No "keep angle" lock on the velocity boxes (offered, declined).

## Anti-goals

- A window that only works for the defaults. Any sensible numbers typed in the boxes must
  produce a correct flight, including straight up (θ = 90), a drop (v0 = 0, y0 > 0),
  Moon gravity, and paths that start at different x0.
- Physics hidden in the UI code. The physics stays in `projectile.py`, marked `# PHYSICS:`.
- Bad input that crashes the window. A box with text that is not a number, g ≤ 0, y0 < 0,
  x max ≤ x min, or y max ≤ y min shows a plain message in the window and keeps the last
  good values.

## Constraints

- Python 3.9, numpy, matplotlib, scipy, pytest. No new packages.
- **No tkinter.** The only Python on the student's Mac is Xcode's 3.9 with Tk 8.5, which
  aborts on macOS 26 ("macOS 26 (2603) or later required"). Checked 2026-11-16; nothing
  newer is installed and the course pins the system Python. So the window is built
  entirely from **matplotlib's own widgets** (`Button`, `TextBox`, `CheckButtons`,
  `RadioButtons`, `Slider`, clickable `Text`) on the `macosx` backend, and tested on the
  `Agg` backend. Verified: all of these build and respond to synthetic clicks headlessly.
  Consequences: no fold-away sections and no dropdowns; the side panel is three labelled
  groups stacked vertically, presets are small buttons, speed is a radio group.
- Layout rules from `CLAUDE.md`: engine in `src/flow_project/`, the runnable file at
  `simulations/ball_no_air/ball_no_air.py` with its settings at the top, tests in `tests/`.
- Beginner-friendly code: plain, commented, no clever tricks.
- Work continues on branch `feature/ball-no-air`, since this revises the checkpoint that
  has not been merged yet.

## How it works (decided)

### Pieces and files

| File | Job | Tested how |
|---|---|---|
| `src/flow_project/projectile.py` | physics engine (exists). Gains a `start_x` argument so a path can begin at x0 ≠ 0. | existing tests + new ones for `start_x` |
| `src/flow_project/launch.py` (new) | `Launch` settings object: x0, y0, v0, θ with the two-way vx/vy link, and a `validate()` that returns a plain-language error string or None. Pure Python. | exact unit tests |
| `src/flow_project/player.py` (rewritten) | `Playback`: shared clock for 1–2 flights. Holds `t`, `paused`, `marks` (path index, x, y, t), auto-pause bookkeeping. Methods `advance`, `toggle_pause`, `step_forward`, `jump_to`, `scrub_to` (no mark), `clear_marks`, `position(i)`. Always moves at least one physics sample per frame (coarse-DT fix carried over). | exact unit tests |
| `src/flow_project/animate.py` (rewritten) | `FlightPlot`: draws N paths on one matplotlib Axes from a `Playback`: ground line, trails, balls, per-path arrows, on-ball numbers, equation cross, ghost markers, clock. `set_limits(xmin, xmax, ymin, ymax)`, `show_arrows`, `show_labels`. Helpers `parse_number`, `auto_limits(flights)`, `label_side`, `format_readout_table`. No tkinter in this file. | Agg-backend tests, no window |
| `src/flow_project/launch_window.py` (new) | `LaunchWindow`: one matplotlib Figure laid out as equation banner (top), plot Axes (left, drawn by `FlightPlot`), time `Slider` + playback bar of widgets (bottom left), side panel of `TextBox`es, `Button`s and `CheckButtons` (right). Wires widgets and key presses to `Launch`/`Playback`; `FuncAnimation` drives frames; `run()` calls `plt.show()`. No physics, no playback rules of its own. | Agg-backend tests, no window: set boxes → Play → a few frames → Pause; click the equation's v0 piece; invalid g shows the status message |
| `simulations/ball_no_air/ball_no_air.py` | settings at the top = the defaults the boxes start with (A, B, g, DT, FRAME_DT, PAUSE_INTERVAL, AUTO_PAUSE, PLAYBACK_SPEED); `main()` opens the window. | existing style of tests |

The old single-path `FlightAnimation`, matplotlib `TextBox`, and `Player` are removed
along with their tests. Nothing else imports them.

### Behaviour details

- **Play** reads every box, validates, builds the flights (`simulate` for A, and B if on),
  auto-fits the axes only if the student has never edited the axis boxes or has pressed
  Auto-fit since, resets the clock to 0, clears nothing else (markers persist until Clear
  markers), and starts playing. Pressing Play while playing pauses; while paused resumes;
  after the end it replays from 0 with the current boxes.
- **Space** = same as the Play button, except while a `TextBox` is capturing keystrokes
  (then space is just a space). Right arrow = Step (same rule). Enter in any box submits
  it and ends typing, so space works right after (carried over from the v1 review fix).
- **Auto-pause** stops at every multiple of the interval, counted from 0. Step moves to
  the next multiple of the interval. Jump goes to the nearest stored sample. Scrubbing
  sets the time directly and pauses without a marker.
- **Equation banner** is a row of matplotlib `Text` pieces across the top of the figure:
  the fixed parts in mathtext (`$\vec r(t) = (x_0 + (v_0\cos\theta)\,t)\,\hat\imath + \ldots$`
  split around the numbers) and each number as its own `Text` with a rounded box and
  `picker=True`. Pieces are laid out left to right using their rendered widths. Clicking a
  number starts typing in the matching `TextBox` (its `begin_typing()`), selects nothing
  (matplotlib text boxes have no selection) but highlights the box's frame in the accent
  colour until the next submit. Two small A / B buttons pick which path the banner shows.
- **Readout table** updates every frame. Rows: x, y, vx, vy, v, range, max height, flight
  time, sim − eq (distance in metres between the simulated ball and the equation's point
  at the current time, 3 decimals).
- **Arrows** use one scale per axis so equal vx and vy look equal on screen (carried over
  from the review fix), sized from the fastest speed among the visible flights. On-ball
  numbers are two lines per ball: `vx 14.1  vy +9.2` and `v 16.9`, flipping to the left of
  the ball near the right edge.
- **Playback speed** 0.25×/0.5×/1× changes the timer interval (`FRAME_DT / speed`).
- **Validation messages** appear in a one-line status `Text` under the playback bar, in the
  orange accent colour, and clear on the next successful Play.
- **Linked boxes update on submit** (Enter or clicking away), because matplotlib text
  boxes only report a value then. Typing vx and pressing Enter rewrites v0 and θ at once.

### Builder's calls (mine; flag if you disagree)

- Each path is simulated with the shared DT; both flights are stored fully before
  playback, like before.
- The time slider has 1000 steps across the longer of the two flights.
- When Path B is switched off its column stays visible but greyed, so its numbers are not
  lost.
- **Any launch direction is allowed** (builder's call after the design check, 2026-11-16).
  The linked boxes make θ < 0 (a downward throw from a height) or θ > 90° (a throw to
  the left) easy to reach, and both are real physics, so they are not errors. The
  equation banner shows the angle as typed (e.g. −30°, 120°). The only launch errors are:
  not a number, y0 < 0, and a ball that starts on the ground heading down or level
  (y0 = 0 with vy ≤ 0 and v0 > 0 gives a zero-length flight; that is allowed and just shows
  the ball sitting at x0).
- Auto-fit axes: x from 1.1 × the lowest x reached (or 0 if all x ≥ 0) to 1.1 × the
  highest x reached (or 0 if all x ≤ 0); y from 0 to 1.25 × the highest point; each
  range at least 1 m wide; if the whole flight is at one x (straight up), centre it with
  ½ m each side. Labels go to the right of the ball unless the ball is in the right 25% of
  the visible x range, then to the left.
- Ghost-marker time labels show one decimal (`1.5s`); the clock shows two (`t = 1.50 s`).
- Window opens at about 1300 × 820 px (figure 13 × 8.2 in at 100 dpi). Widgets are placed
  in figure fractions so resizing keeps the layout.
- Gravity preset buttons fill the g box and submit it; they do not launch.

### Tests (must pass before done)

- `Launch`: setting vx/vy updates v0/θ and back, round-trips within 1e-9; validate catches
  non-numbers, g ≤ 0, y0 < 0, axis max ≤ min; messages are plain English.
- `simulate(start_x=5)`: x[0] == 5, range measured from x0 matches the formula.
- `Playback` with two flights of different lengths: shared t, each path's position stops
  at its own landing; auto-pause at exact multiples; step; jump clamps; scrub adds no
  mark; every other pause adds one mark per visible path; coarse DT still finishes.
- `FlightPlot` (Agg): two balls at their own positions; B hidden when off; equation cross
  within 1% of range of the ball for no-air; arrows equal on screen for equal vx, vy;
  set_limits applied; straight-up case visible; label flip near right edge.
- `launch_window` (Agg): window builds; submitting the vx box updates the θ box text;
  clicking the equation's v0 piece begins typing in the v0 box; Play builds two flights;
  a few frames advance the clock; invalid g shows the status message and does not crash;
  space is ignored while a box is capturing keystrokes; Path B off hides the second ball.
- `ball_no_air.main(show=False)` returns the window object without calling `plt.show()`.

## Left to the builder

- Exact fonts, padding, colours (follow the mockup's spirit; matplotlib widgets look
  plainer).
- Exact figure-coordinate rectangles for every widget, as long as the four areas of the
  mockup are kept and nothing overlaps at the default window size (about 1300 × 820 px).
- Whether the readout is one monospace `Text` block or a small table `Axes`.
