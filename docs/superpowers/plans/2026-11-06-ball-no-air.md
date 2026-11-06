# Ball With No Air Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A time-stepped projectile simulation (gravity only) with a matplotlib animation showing the ball, its velocity components as arrows and numbers, a clock, pause/step/auto-pause/jump-to-time controls, and ghost markers at every pause.

**Architecture:** The physics engine (`projectile.py`) runs the whole flight first with tiny Euler steps and stores arrays. A pure-Python `Player` (`player.py`) owns playback state (current sample, paused, marks) with no matplotlib in it, so it is fully unit-testable. `animate.py` is the only matplotlib code and just draws whatever the `Player` says. `simulations/ball_no_air/ball_no_air.py` is the file the student runs and edits; its settings are at the top.

**Tech Stack:** Python 3.9, numpy 2.0, matplotlib 3.9 (`FuncAnimation`, `TextBox` widget, Agg backend in tests), pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-ball-no-air-design.md`

## Global Constraints

- Python 3.9 compatible (no `match`, no `X | Y` type unions, use `typing.Optional`/`Tuple`/`List`).
- No new dependencies beyond `requirements.txt` (numpy, matplotlib, scipy, pytest).
- Imports use the `src.flow_project.<module>` and `simulations.<name>.<name>` roots (`pytest.ini` sets `pythonpath = .`).
- Every new function gets tests in the same task. `make test` must pass and must never open a window.
- Code is for a high-school student: plain loops, comments on every physics line, settings at the top of the runnable file with comments. Each physics line carries a `# PHYSICS:` comment prefix so the student can grep for them.
- Commits are small, on branch `feature/ball-no-air`, never on `main`. Each commit message ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Default settings (from the mockup): speed 20 m/s, angle 45°, g 9.8 m/s², start height 0 m, DT 0.001 s, FRAME_DT 0.02 s, pause interval 0.5 s, auto-pause on, playback speed 0.5.

## Review Focus

1. **Straight up (angle 90°) or straight drop (speed 0 from a height):** range is 0, so axis limits must not collapse to zero width. Test in Task 4 (`axis_limits` minimums) and Task 1 (`simulate` at 90° has vx == 0 everywhere).
2. **Zero-length flight (angle 0°, start height 0):** the ball is already on the ground. `simulate` must return a single sample, not loop forever or crash, and `Player` must report finished at once. Tests in Task 1 and Task 2.
3. **Bad gravity (g <= 0):** the formulas divide by g and the loop would never end. `simulate` and `exact_flight_time` raise `ValueError` with a plain message. Test in Task 1.
4. **Pause interval that is not a multiple of FRAME_DT (e.g. 0.25 with 0.02):** auto-pause must land on exactly 0.25 s (nearest stored sample), not on the next frame after it. Test in Task 2.
5. **Jump box input that is not a clean number ("", "abc", "1,25", "-2", "999"):** blank/garbage/negative are ignored, past-the-end clamps to the landing time. Test in Task 3.

---

### Task 1: Physics engine

**Files:**
- Create: `src/flow_project/projectile.py`
- Test: `tests/test_projectile.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  class Flight:  # dataclass holding numpy arrays, all the same length
      t: np.ndarray; x: np.ndarray; y: np.ndarray; vx: np.ndarray; vy: np.ndarray
      @property speed(self) -> np.ndarray        # hypot(vx, vy)
      @property flight_time(self) -> float       # t[-1]
      @property max_height(self) -> float        # y.max()
      @property range(self) -> float             # x[-1]
      def index_at_time(self, t: float) -> int   # index of the stored sample nearest t, clamped to [0, len-1]

  def step(x: float, y: float, vx: float, vy: float, dt: float, g: float) -> Tuple[float, float, float, float]
  def simulate(speed: float, angle_deg: float, g: float = 9.8, start_height: float = 0.0, dt: float = 0.001) -> Flight
  def exact_position(t: float, speed: float, angle_deg: float, g: float = 9.8, start_height: float = 0.0) -> Tuple[float, float]
  def exact_velocity(t: float, speed: float, angle_deg: float, g: float = 9.8) -> Tuple[float, float]
  def exact_flight_time(speed: float, angle_deg: float, g: float = 9.8, start_height: float = 0.0) -> float
  ```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_projectile.py
import math
import numpy as np
import pytest

from src.flow_project.projectile import (
    Flight, step, simulate, exact_position, exact_velocity, exact_flight_time,
)


def test_step_changes_velocity_then_position():
    # one slice: vy drops by g*dt, then position moves with the NEW velocity
    x, y, vx, vy = step(0.0, 0.0, 3.0, 4.0, dt=0.1, g=10.0)
    assert vx == pytest.approx(3.0)
    assert vy == pytest.approx(3.0)
    assert x == pytest.approx(0.3)
    assert y == pytest.approx(0.3)


def test_exact_formulas_at_known_point():
    # 20 m/s at 45°: vx = vy = 14.142...; after 1 s with g=9.8
    x, y = exact_position(1.0, 20.0, 45.0, g=9.8)
    vx, vy = exact_velocity(1.0, 20.0, 45.0, g=9.8)
    assert x == pytest.approx(14.1421, abs=1e-3)
    assert y == pytest.approx(14.1421 - 4.9, abs=1e-3)
    assert vx == pytest.approx(14.1421, abs=1e-3)
    assert vy == pytest.approx(14.1421 - 9.8, abs=1e-3)


def test_exact_flight_time_flat_ground():
    # t = 2 v sin(a) / g
    assert exact_flight_time(20.0, 45.0, g=9.8) == pytest.approx(2 * 20 * math.sin(math.radians(45)) / 9.8)


def test_exact_flight_time_with_start_height():
    # dropped from 10 m with no speed: t = sqrt(2h/g)
    assert exact_flight_time(0.0, 0.0, g=9.8, start_height=10.0) == pytest.approx(math.sqrt(20 / 9.8))


def test_simulate_matches_exact_formulas():
    flight = simulate(20.0, 45.0, g=9.8, start_height=0.0, dt=0.001)
    tol = 0.01 * flight.range
    for t_check in (0.5, 1.0, 1.5, 2.0):
        i = flight.index_at_time(t_check)
        ex, ey = exact_position(flight.t[i], 20.0, 45.0)
        evx, evy = exact_velocity(flight.t[i], 20.0, 45.0)
        assert flight.x[i] == pytest.approx(ex, abs=tol)
        assert flight.y[i] == pytest.approx(ey, abs=tol)
        assert flight.vx[i] == pytest.approx(evx, abs=1e-6)
        assert flight.vy[i] == pytest.approx(evy, abs=1e-6)


def test_vx_never_changes():
    flight = simulate(20.0, 30.0)
    assert np.allclose(flight.vx, flight.vx[0])


def test_range_and_max_height_match_formulas():
    flight = simulate(20.0, 45.0, g=9.8)
    exact_range = 20.0 ** 2 * math.sin(math.radians(90)) / 9.8
    exact_hmax = (20.0 * math.sin(math.radians(45))) ** 2 / (2 * 9.8)
    assert flight.range == pytest.approx(exact_range, rel=0.01)
    assert flight.max_height == pytest.approx(exact_hmax, rel=0.01)
    assert flight.flight_time == pytest.approx(exact_flight_time(20.0, 45.0), rel=0.01)


def test_simulate_stops_at_ground():
    flight = simulate(20.0, 45.0)
    assert flight.y[-1] == pytest.approx(0.0, abs=1e-9)
    assert (flight.y >= -1e-9).all()
    assert len(flight.t) == len(flight.x) == len(flight.y) == len(flight.vx) == len(flight.vy)


def test_simulate_from_height_lands_on_ground():
    flight = simulate(10.0, 0.0, start_height=5.0)
    assert flight.y[0] == pytest.approx(5.0)
    assert flight.y[-1] == pytest.approx(0.0, abs=1e-9)
    assert flight.flight_time == pytest.approx(exact_flight_time(10.0, 0.0, start_height=5.0), rel=0.01)


def test_higher_gravity_shorter_range():
    assert simulate(20.0, 45.0, g=20.0).range < simulate(20.0, 45.0, g=9.8).range


def test_45_degrees_goes_farthest_on_flat_ground():
    r45 = simulate(20.0, 45.0).range
    assert r45 > simulate(20.0, 30.0).range
    assert r45 > simulate(20.0, 60.0).range


def test_straight_up_has_zero_vx():
    flight = simulate(20.0, 90.0)
    assert np.allclose(flight.vx, 0.0)
    assert flight.range == pytest.approx(0.0, abs=1e-6)
    assert flight.max_height > 0


def test_zero_length_flight_is_single_sample():
    flight = simulate(20.0, 0.0, start_height=0.0)
    assert len(flight.t) == 1
    assert flight.flight_time == 0.0


def test_bad_gravity_raises():
    with pytest.raises(ValueError):
        simulate(20.0, 45.0, g=0.0)
    with pytest.raises(ValueError):
        exact_flight_time(20.0, 45.0, g=-9.8)


def test_speed_property_and_index_at_time():
    flight = simulate(20.0, 45.0, dt=0.001)
    assert flight.speed[0] == pytest.approx(20.0)
    assert flight.index_at_time(-5.0) == 0
    assert flight.index_at_time(1e9) == len(flight.t) - 1
    i = flight.index_at_time(1.25)
    assert flight.t[i] == pytest.approx(1.25, abs=0.0005)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_projectile.py -v`
Expected: FAIL at import, `ModuleNotFoundError: No module named 'src.flow_project.projectile'`

- [ ] **Step 3: Implement `src/flow_project/projectile.py`**

`Flight` is a `@dataclass`. `step` is semi-implicit Euler: update `vy` first (`vy - g*dt`), then `x += vx*dt`, `y += vy_new*dt`. Mark those three lines `# PHYSICS:`. `simulate` validates `g > 0` (`ValueError("gravity must be a positive number")`), converts the angle with `math.radians`, starts at `(0, start_height)`, and loops calling `step` while `y >= 0`. When a step crosses below ground, linearly interpolate between the last in-air sample and the below-ground sample to find where `y == 0`, append that clipped sample (with the interpolated `t`), and stop. If the ball starts on the ground with `vy <= 0`, return the single starting sample. Build the arrays with `np.array` at the end. `index_at_time` uses `np.searchsorted` or `np.argmin(np.abs(t - target))`, clamped. `exact_*` are the textbook formulas; `exact_flight_time` solves `0 = h + vy t - g t²/2` for the positive root.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_projectile.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/flow_project/projectile.py tests/test_projectile.py
git commit -m "Add time-stepped projectile physics engine with exact-formula tests"
```

---

### Task 2: Playback state (`Player`)

**Files:**
- Create: `src/flow_project/player.py`
- Test: `tests/test_player.py`

**Interfaces:**
- Consumes: `Flight` from Task 1 (`flight.t`, `.x`, `.y`, `.vx`, `.vy`, `.speed`, `.flight_time`, `.index_at_time`).
- Produces:
  ```python
  def next_pause_time(current_t: float, interval: float) -> float
      # smallest k*interval strictly greater than current_t (tolerance 1e-9); interval <= 0 -> ValueError

  class Player:
      def __init__(self, flight: Flight, frame_dt: float = 0.02, pause_interval: float = 0.5, auto_pause: bool = True)
      index: int                      # current sample
      paused: bool
      marks: List[Tuple[float, float, float]]   # (x, y, t) ghost markers, in order added
      @property t, x, y, vx, vy, speed -> float  # values at the current sample
      @property finished -> bool      # index is the last sample
      def advance(self) -> None       # one animation frame forward (no-op if paused or finished)
      def toggle_pause(self) -> None  # pausing adds a mark; resuming does not
      def step_forward(self) -> None  # jump ahead by pause_interval, pause, add mark
      def jump_to(self, t: float) -> None  # go to nearest sample to t (clamped), pause, add mark
  ```
  Marks are only added when a pause lands at a time that doesn't already have a mark. Pausing at the end of the flight (finished) still adds a mark.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_player.py
import pytest

from src.flow_project.projectile import simulate
from src.flow_project.player import Player, next_pause_time


@pytest.fixture
def flight():
    return simulate(20.0, 45.0, dt=0.001)


def test_next_pause_time():
    assert next_pause_time(0.0, 0.5) == pytest.approx(0.5)
    assert next_pause_time(0.49, 0.5) == pytest.approx(0.5)
    assert next_pause_time(0.5, 0.5) == pytest.approx(1.0)
    assert next_pause_time(1.2, 0.25) == pytest.approx(1.25)
    with pytest.raises(ValueError):
        next_pause_time(0.0, 0.0)


def test_starts_at_beginning_playing(flight):
    p = Player(flight)
    assert p.index == 0 and p.t == 0.0 and not p.paused and not p.finished
    assert p.speed == pytest.approx(20.0)


def test_advance_moves_one_frame(flight):
    p = Player(flight, frame_dt=0.02, auto_pause=False)
    p.advance()
    assert p.t == pytest.approx(0.02, abs=0.0005)
    p.advance()
    assert p.t == pytest.approx(0.04, abs=0.0005)


def test_advance_does_nothing_when_paused(flight):
    p = Player(flight, auto_pause=False)
    p.toggle_pause()
    p.advance()
    assert p.t == 0.0


def test_auto_pause_lands_exactly_on_interval(flight):
    p = Player(flight, frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(0.25, abs=0.0005)
    assert p.marks[-1][2] == pytest.approx(0.25, abs=0.0005)
    p.toggle_pause()  # resume
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(0.5, abs=0.0005)
    assert len(p.marks) == 2


def test_space_pause_adds_mark_and_resume_does_not(flight):
    p = Player(flight, auto_pause=False)
    for _ in range(10):
        p.advance()
    p.toggle_pause()
    assert p.paused and len(p.marks) == 1
    assert p.marks[0][2] == pytest.approx(p.t)
    p.toggle_pause()
    assert not p.paused and len(p.marks) == 1


def test_step_forward(flight):
    p = Player(flight, pause_interval=0.5, auto_pause=False)
    p.step_forward()
    assert p.paused and p.t == pytest.approx(0.5, abs=0.0005)
    p.step_forward()
    assert p.t == pytest.approx(1.0, abs=0.0005)
    assert [round(m[2], 2) for m in p.marks] == [0.5, 1.0]


def test_step_forward_clamps_to_end(flight):
    p = Player(flight, pause_interval=100.0)
    p.step_forward()
    assert p.finished and p.t == pytest.approx(flight.flight_time)


def test_jump_to(flight):
    p = Player(flight)
    p.jump_to(1.25)
    assert p.paused
    assert p.t == pytest.approx(1.25, abs=0.0005)
    assert p.x == pytest.approx(flight.x[p.index])
    assert p.marks[-1] == (flight.x[p.index], flight.y[p.index], flight.t[p.index])


def test_jump_clamps(flight):
    p = Player(flight)
    p.jump_to(999.0)
    assert p.finished
    p.jump_to(-3.0)
    assert p.index == 0


def test_jump_then_resume_auto_pauses_at_next_interval(flight):
    p = Player(flight, frame_dt=0.02, pause_interval=0.5, auto_pause=True)
    p.jump_to(1.1)
    p.toggle_pause()
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(1.5, abs=0.0005)


def test_no_duplicate_mark_at_same_time(flight):
    p = Player(flight)
    p.jump_to(1.0)
    p.toggle_pause()   # resume
    p.toggle_pause()   # pause again at the same spot
    assert len(p.marks) == 1


def test_finishes_at_end(flight):
    p = Player(flight, auto_pause=False)
    for _ in range(10000):
        p.advance()
    assert p.finished and p.t == pytest.approx(flight.flight_time)


def test_zero_length_flight_is_finished_immediately():
    p = Player(simulate(20.0, 0.0))
    assert p.finished
    p.advance()
    assert p.index == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_player.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'src.flow_project.player'`

- [ ] **Step 3: Implement `src/flow_project/player.py`**

Keep `_next_stop: Optional[float]` (None when auto-pause is off), set to `next_pause_time(self.t, pause_interval)` at construction and after every pause/jump. `advance()`: target = `t + frame_dt`; if `_next_stop` is not None and `target >= _next_stop - 1e-9`, set target to `_next_stop` and pause after moving. Move with `index = flight.index_at_time(min(target, flight.flight_time))`. A private `_pause_here()` sets `paused = True`, appends `(x, y, t)` unless the last mark has the same `t`, and recomputes `_next_stop`. `toggle_pause()` on resume just flips `paused` (no mark).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_player.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/flow_project/player.py tests/test_player.py
git commit -m "Add Player playback state with pause, step, auto-pause, jump and marks"
```

---

### Task 3: Animation helpers (pure functions)

**Files:**
- Create: `src/flow_project/animate.py` (helpers only in this task; drawing comes in Task 4)
- Test: `tests/test_animate.py`

**Interfaces:**
- Consumes: `Flight` (Task 1).
- Produces:
  ```python
  def parse_jump_time(text: str, flight_time: float) -> Optional[float]
      # "1.25" -> 1.25; " 2 " -> 2.0; "" / "abc" / "1,25" / "-2" -> None; "999" -> flight_time
  def axis_limits(flight: Flight) -> Tuple[float, float]
      # (xmax, ymax) = (max(range*1.1, 1.0), max(max_height*1.25, 1.0))
  def label_side(x: float, xmax: float) -> str
      # "left" when the ball is in the right 25% of the plot (labels go to its left), else "right"
  def format_readout(t, x, y, vx, vy, speed, max_height, rng) -> str
      # multi-line side-panel text, one value per line, 2 decimals for t, 1 decimal for the rest, with units
  ```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_animate.py
import pytest

from src.flow_project.projectile import simulate
from src.flow_project.animate import parse_jump_time, axis_limits, label_side, format_readout


@pytest.mark.parametrize("text,expected", [
    ("1.25", 1.25), (" 2 ", 2.0), ("0", 0.0), ("", None), ("abc", None),
    ("1,25", None), ("-2", None), ("999", 2.9),
])
def test_parse_jump_time(text, expected):
    assert parse_jump_time(text, flight_time=2.9) == expected


def test_axis_limits_fit_flight():
    flight = simulate(20.0, 45.0)
    xmax, ymax = axis_limits(flight)
    assert xmax == pytest.approx(flight.range * 1.1)
    assert ymax == pytest.approx(flight.max_height * 1.25)


def test_axis_limits_never_collapse():
    xmax, ymax = axis_limits(simulate(20.0, 90.0))   # straight up: range 0
    assert xmax >= 1.0
    xmax, ymax = axis_limits(simulate(20.0, 0.0))    # no flight at all
    assert xmax >= 1.0 and ymax >= 1.0


def test_label_side():
    assert label_side(10.0, 100.0) == "right"
    assert label_side(80.0, 100.0) == "left"


def test_format_readout():
    text = format_readout(t=1.234, x=10.0, y=5.55, vx=14.14, vy=-2.0, speed=14.28, max_height=10.2, rng=40.8)
    lines = text.splitlines()
    assert lines[0] == "t = 1.23 s"
    assert "x = 10.0 m" in lines
    assert "vy = -2.0 m/s" in lines
    assert "range = 40.8 m" in lines
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_animate.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'src.flow_project.animate'`

- [ ] **Step 3: Implement the four helpers in `src/flow_project/animate.py`**

`parse_jump_time` uses `float(text.strip())` inside `try/except ValueError`, rejects negatives, clamps with `min`. Readout lines in order: `t`, `x`, `y`, `vx`, `vy`, `speed`, `max height`, `range`. No matplotlib import needed yet.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_animate.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/flow_project/animate.py tests/test_animate.py
git commit -m "Add animation helper functions for jump parsing, axis limits, labels"
```

---

### Task 4: Matplotlib animation (`FlightAnimation`)

**Files:**
- Modify: `src/flow_project/animate.py` (add the class)
- Test: `tests/test_animate.py` (add headless tests)

**Interfaces:**
- Consumes: `Flight` (Task 1), `Player` (Task 2: `.advance()`, `.toggle_pause()`, `.step_forward()`, `.jump_to()`, `.t/.x/.y/.vx/.vy/.speed`, `.paused`, `.marks`, `.index`), helpers (Task 3).
- Produces:
  ```python
  class FlightAnimation:
      def __init__(self, flight: Flight, player: Player, playback_speed: float = 0.5,
                   title: str = "Ball with no air", arrow_scale: float = 0.1)
      fig: matplotlib.figure.Figure
      player: Player            # stored as given
      textbox: matplotlib.widgets.TextBox
      ball, trail, marks_scatter, vx_arrow, vy_arrow, vx_text, vy_text, speed_text, clock_text, readout_text  # artists
      # text formats (tests depend on these):
      #   vx_text:    f"vx {vx:.1f}"      vy_text: f"vy {vy:+.1f}"      speed_text: f"v {speed:.1f}"
      #   clock_text: f"t = {t:.2f} s" + (" (paused)" if player.paused else "")
      #   readout_text: format_readout(...) from Task 3
      def draw_frame(self, frame_number: int) -> None   # calls player.advance() then redraws from player state
      def on_key(self, event) -> None    # " " -> toggle_pause; "right" -> step_forward
      def on_jump(self, text: str) -> None   # TextBox submit handler: parse_jump_time -> player.jump_to
      def run(self) -> None   # builds FuncAnimation with interval = frame_dt / playback_speed * 1000 ms and calls plt.show()
  ```
  Colours: ball and vx arrow/text `#0b6e8e`, vy arrow/text `#c2491d`, speed text `#4a3e8a`, marks grey. Arrows are `ax.annotate` arrows (or `FancyArrowPatch`) in data units with length `arrow_scale * velocity` so they scale with speed. Clock text top-right: `t = 1.25 s`, plus ` (paused)` when paused. Ghost marks are hollow grey circles with the time as `f"{t:.1f}s"` underneath. Trail is `ax.plot` of `flight.x[:index+1]`, `flight.y[:index+1]` dotted. The TextBox is placed under the axes with label `Jump to t (s)`. Axes labelled `x (m)` and `y (m)`; the ground is a solid line at y = 0.

- [ ] **Step 1: Write the failing headless tests (append to `tests/test_animate.py`)**

```python
import matplotlib
matplotlib.use("Agg")  # no window during tests

from src.flow_project.player import Player
from src.flow_project.animate import FlightAnimation


@pytest.fixture
def anim():
    flight = simulate(20.0, 45.0)
    player = Player(flight, frame_dt=0.02, pause_interval=0.5, auto_pause=True)
    return FlightAnimation(flight, player)


def test_first_frame_draws_ball_at_start(anim):
    anim.draw_frame(0)
    x, y = anim.ball.get_data()
    assert float(x[0]) == pytest.approx(anim.player.x)
    assert "vx 14.1" in anim.vx_text.get_text()
    assert anim.clock_text.get_text().startswith("t = ")


def test_frames_advance_and_update_labels(anim):
    for i in range(5):
        anim.draw_frame(i)
    assert anim.player.index > 0
    assert f"t = {anim.player.t:.2f} s" in anim.clock_text.get_text()
    assert f"vy {anim.player.vy:+.1f}" in anim.vy_text.get_text()
    assert len(anim.trail.get_xdata()) == anim.player.index + 1


def test_space_key_pauses_and_marks(anim):
    class Ev: key = " "
    anim.draw_frame(0); anim.draw_frame(1)
    anim.on_key(Ev())
    anim.draw_frame(2)
    assert anim.player.paused
    assert "(paused)" in anim.clock_text.get_text()
    assert len(anim.marks_scatter.get_offsets()) == 1


def test_right_key_steps_forward(anim):
    class Ev: key = "right"
    anim.on_key(Ev())
    anim.draw_frame(0)
    assert anim.player.t == pytest.approx(0.5, abs=0.0005)


def test_jump_box_moves_ball(anim):
    anim.on_jump("1.25")
    anim.draw_frame(0)
    assert anim.player.t == pytest.approx(1.25, abs=0.0005)
    assert "1.25" in anim.clock_text.get_text()
    anim.on_jump("garbage")
    assert anim.player.t == pytest.approx(1.25, abs=0.0005)


def test_readout_text_matches_player(anim):
    anim.on_jump("1.0")
    anim.draw_frame(0)
    assert f"speed = {anim.player.speed:.1f} m/s" in anim.readout_text.get_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_animate.py -v`
Expected: new tests FAIL with `ImportError: cannot import name 'FlightAnimation'`; Task 3 tests still PASS.

- [ ] **Step 3: Implement `FlightAnimation` in `src/flow_project/animate.py`**

Build the figure in `__init__` (`plt.subplots`, `fig.subplots_adjust(bottom=0.2)` to leave room for the TextBox, `matplotlib.widgets.TextBox` at `fig.add_axes([0.25, 0.05, 0.3, 0.06])`). Connect `fig.canvas.mpl_connect("key_press_event", self.on_key)` and `textbox.on_submit(self.on_jump)`. Create every artist once; `draw_frame` only updates data/text/positions. Put the velocity labels at `(x ± offset, y)` using `label_side` so they flip near the right edge. Keep the TextBox from eating the space bar: in `on_key`, ignore keys while the TextBox is active (`self.textbox.capturekeystrokes` is True… check the attribute name in matplotlib 3.9; if unavailable, use the `event.inaxes is self.textbox.ax` check). `run()` must keep a reference to the `FuncAnimation` object on `self` or it will be garbage-collected.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_animate.py -v`
Expected: all PASS, no window opens

- [ ] **Step 5: Commit**

```bash
git add src/flow_project/animate.py tests/test_animate.py
git commit -m "Add matplotlib FlightAnimation with arrows, labels, clock, controls"
```

---

### Task 5: The runnable simulation file and launcher

**Files:**
- Create: `simulations/__init__.py`, `simulations/ball_no_air/__init__.py` (empty)
- Create: `simulations/ball_no_air/ball_no_air.py`
- Modify: `src/flow_project/main.py` (replace the demo body)
- Modify: `Makefile` (`run` target)
- Modify: `simulations/ball_no_air/README.md`, `CLAUDE.md` Layout section, `README.md`
- Test: `tests/test_ball_no_air.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: `simulate` (Task 1), `Player` (Task 2), `FlightAnimation` (Task 4).
- Produces:
  ```python
  # simulations/ball_no_air/ball_no_air.py  — settings block at top, all UPPER_CASE with a comment each:
  LAUNCH_SPEED = 20.0        # m/s
  LAUNCH_ANGLE = 45.0        # degrees above the ground
  GRAVITY = 9.8              # m/s²
  START_HEIGHT = 0.0         # m
  DT = 0.001                 # physics time slice, s
  FRAME_DT = 0.02            # simulated seconds per animation frame
  PAUSE_INTERVAL = 0.5       # s, for auto-pause and the right-arrow step
  AUTO_PAUSE = True
  PLAYBACK_SPEED = 0.5       # 1.0 = real time, 0.5 = half speed

  def build_flight() -> Flight
  def build_player(flight: Flight) -> Player
  def main(show: bool = True) -> FlightAnimation   # builds everything; calls .run() only when show is True

  # src/flow_project/main.py
  def load_simulation(name: str) -> ModuleType   # importlib.import_module(f"simulations.{name}.{name}")
  def main(argv: Optional[List[str]] = None) -> None   # name = argv[0] if given else "ball_no_air"; load and call .main()
  ```
  Makefile: `SIM ?= ball_no_air` and `run: setup` → `$(PYTHON) -m src.flow_project.main $(SIM)` (keep the `setup` dependency).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ball_no_air.py
import matplotlib
matplotlib.use("Agg")
import pytest

from simulations.ball_no_air import ball_no_air as sim


def test_settings_exist_with_defaults():
    assert sim.LAUNCH_SPEED == 20.0 and sim.LAUNCH_ANGLE == 45.0 and sim.GRAVITY == 9.8
    assert sim.DT == 0.001 and sim.FRAME_DT == 0.02 and sim.PAUSE_INTERVAL == 0.5
    assert sim.AUTO_PAUSE is True and sim.PLAYBACK_SPEED == 0.5


def test_build_flight_uses_settings():
    flight = sim.build_flight()
    assert flight.speed[0] == pytest.approx(sim.LAUNCH_SPEED)
    assert flight.range > 0


def test_main_without_show_builds_animation():
    anim = sim.main(show=False)
    assert anim.player.t == 0.0
    anim.draw_frame(0)
```

```python
# tests/test_main.py
import matplotlib
matplotlib.use("Agg")
import pytest

from src.flow_project.main import load_simulation


def test_load_simulation_finds_ball_no_air():
    module = load_simulation("ball_no_air")
    assert callable(module.main)


def test_load_simulation_unknown_name():
    with pytest.raises(ModuleNotFoundError):
        load_simulation("does_not_exist")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_ball_no_air.py tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError` for `simulations.ball_no_air.ball_no_air` and `ImportError` for `load_simulation`.

- [ ] **Step 3: Create `ball_no_air.py`, rewrite `main.py`, update the Makefile**

`ball_no_air.py` has a docstring explaining what it is, the settings block, the three functions, and `if __name__ == "__main__": main()`. `main.py`'s `main()` passes `show=True` by default; keep `math_utils` untouched.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_ball_no_air.py tests/test_main.py -v`
Expected: all PASS

- [ ] **Step 5: Run the real thing once and look at it**

Run: `make run`
Expected: a window opens, the ball flies at half speed and auto-pauses at 0.5 s with a ghost marker; space resumes; right arrow steps; typing `1.25` in the box and pressing Enter jumps there. Close the window. Fix anything visibly wrong (overlapping labels, arrows off-scale), then re-run `make test`.

- [ ] **Step 6: Update the docs**

- `simulations/ball_no_air/README.md`: replace "(coming next)" with the actual controls (space, right arrow, jump box) and the list of settings.
- `README.md` (project root): one paragraph on what the project is, `make run`, `make run SIM=<name>`, and where simulations live.
- `CLAUDE.md` Layout section: add a line `- simulations/<name>/<name>.py — one runnable simulation per folder, settings at the top; shared engine code stays in src/flow_project/.`

- [ ] **Step 7: Run the full suite and commit**

Run: `make test`
Expected: all tests PASS (math_utils, projectile, player, animate, ball_no_air, main).

```bash
git add simulations src/flow_project/main.py Makefile README.md CLAUDE.md tests/test_ball_no_air.py tests/test_main.py
git commit -m "Add runnable ball_no_air simulation, launcher, and docs"
```

---

### Task 6: Code review before merge

- [ ] **Step 1:** Run `make test` one final time; all green.
- [ ] **Step 2:** Use `superpowers:requesting-code-review` on the whole branch against the spec. Fix anything it finds, with tests, and commit.
- [ ] **Step 3:** Stop. Do **not** merge. Tell the student the checkpoint is ready for their teacher's approval, per `CLAUDE.md`.
