# Two-Path Launch Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v1 single-path window with a matplotlib-widget window where every launch value is typed on screen, the path equation is shown with live numbers, two paths play at once, Play just plays, and the axes are adjustable.

**Architecture:** The physics engine (`projectile.py`) is unchanged except for a `start_x` argument. Three pure-Python pieces carry all the rules: `Launch` (one path's inputs with the vx/vy ↔ v0/θ link and validation), `Playback` (a shared clock over 1–2 flights with pause/step/jump/scrub/marks), and `FlightPlot` (draws a `Playback` onto one Axes). `LaunchWindow` is only wiring: it lays matplotlib widgets out on one Figure and forwards clicks and keys to those pieces. Everything is tested on the Agg backend; nothing opens a window under `make test`.

**Tech Stack:** Python 3.9, numpy 2.0, matplotlib 3.9 (`widgets.TextBox/Button/CheckButtons/RadioButtons/Slider`, `FuncAnimation`, pick events, mathtext), pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-two-path-launch-window-design.md`

## Global Constraints

- Python 3.9 compatible (no `match`, no `X | Y` unions; use `typing.Optional/List/Tuple/Dict`).
- No new packages. **No tkinter** (Tk 8.5 aborts on macOS 26). UI = matplotlib widgets; tests set `matplotlib.use("Agg")` before importing anything that draws.
- Imports use `src.flow_project.<module>` and `simulations.ball_no_air.ball_no_air`.
- Every new function/class gets tests in the same task. `make test` passes with no window.
- Physics lines carry `# PHYSICS:`; code is plain and commented for a beginner; settings at the top of `ball_no_air.py` with comments.
- Branch `feature/ball-no-air`; small commits ending with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Colours: Path A `#0b6e8e`, Path B `#c2491d`, speed label `#4a3e8a`, markers `#8a8f98`, equation cross black.
- Defaults (from the spec/mockup): A = (x0 0, y0 0, v0 20, θ 45); B = (x0 0, y0 5, v0 20, θ 30); g 9.8; DT 0.001; FRAME_DT 0.02; PAUSE_INTERVAL 0.5; AUTO_PAUSE False; PLAYBACK_SPEED 0.5; Path B on.
- Presets: Earth 9.8, Moon 1.6, Mars 3.7, Jupiter 24.8. Speeds: 0.25×, 0.5×, 1×.
- The v1 `Player`, `FlightAnimation`, matplotlib `TextBox` jump box and their tests are deleted in Tasks 3–4; nothing else may import them afterwards.

## Review Focus

1. **Two flights of different length:** after the shorter one lands, its ball must sit at its landing point while the clock keeps running for the other; readout and cross for the landed path show landing values. Pinned in Task 3 (`test_landed_path_stays_at_landing`) and Task 4 (`test_landed_ball_stays_put`).
2. **Downward or leftward throws (θ < 0 or θ > 90°) reached through the vx/vy boxes:** must produce a flight, auto-fit axes that contain it, and readable labels. Pinned in Task 1 (`test_leftward_and_downward_throws`), Task 4 (`test_auto_limits_negative_x`, `test_label_side_uses_visible_range`).
3. **Garbage in any box at Play time** (blank, "abc", "1,25", g = 0, y0 = −3, x max ≤ x min): a plain message appears, nothing crashes, the previous flight keeps playing/paused as it was. Pinned in Task 2 (`test_validate_messages`) and Task 5 (`test_bad_input_shows_status_and_keeps_old_flight`).
4. **Coarse DT (0.05) or tiny FRAME_DT:** playback must still reach the end and auto-pause at exact multiples (the v1 freeze bug). Pinned in Task 3 (`test_coarse_dt_reaches_end`).
5. **Keyboard focus:** space typed inside a text box must not toggle play; Enter in a box must end typing so the next space works. Pinned in Task 5 (`test_space_ignored_while_typing`, `test_enter_in_box_ends_typing`).

---

### Task 1: Engine gains a start x

**Files:**
- Modify: `src/flow_project/projectile.py` (`simulate`, `exact_position`, `Flight.range`)
- Test: `tests/test_projectile.py` (append)

**Interfaces:**
- Produces:
  ```python
  def simulate(speed, angle_deg, g=9.8, start_height=0.0, dt=0.001, start_x=0.0) -> Flight
  def exact_position(t, speed, angle_deg, g=9.8, start_height=0.0, start_x=0.0) -> Tuple[float, float]
  Flight.range -> float   # now x[-1] - x[0] (distance travelled sideways, can be negative for leftward throws)
  Flight.x0 -> float      # new property: x[0]
  ```

- [ ] **Step 1: Append the failing tests**

```python
def test_simulate_start_x_shifts_the_whole_path():
    base = simulate(20.0, 45.0)
    shifted = simulate(20.0, 45.0, start_x=5.0)
    assert shifted.x[0] == pytest.approx(5.0)
    assert shifted.x0 == pytest.approx(5.0)
    assert shifted.range == pytest.approx(base.range, rel=1e-6)
    assert shifted.x[-1] == pytest.approx(base.x[-1] + 5.0, rel=1e-6)
    ex, _ = exact_position(1.0, 20.0, 45.0, start_x=5.0)
    assert ex == pytest.approx(5.0 + 20.0 * math.cos(math.radians(45)))


def test_leftward_and_downward_throws():
    left = simulate(20.0, 135.0)           # thrown up and to the left
    assert left.x[-1] < 0 and left.range < 0
    down = simulate(10.0, -30.0, start_height=10.0)   # thrown downward off a roof
    assert down.vy[0] < 0 and down.y[-1] == pytest.approx(0.0, abs=1e-9)
    assert down.flight_time < exact_flight_time(0.0, 0.0, start_height=10.0)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_projectile.py -q`
Expected: 2 failed (`TypeError: unexpected keyword 'start_x'`), rest pass.

- [ ] **Step 3: Implement** `start_x` in both functions (start at `(start_x, start_height)`), `Flight.x0` property, and change `range` to `float(self.x[-1] - self.x[0])`. Update the docstring that claimed `exact_*` feeds the readouts (they feed the equation cross now).

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_projectile.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/flow_project/projectile.py tests/test_projectile.py
git commit -m "Engine: start_x for paths that begin away from the origin"
```

---

### Task 2: `Launch` settings with linked velocity boxes and validation

**Files:**
- Create: `src/flow_project/launch.py`
- Test: `tests/test_launch.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass
  class Launch:
      x0: float = 0.0; y0: float = 0.0; v0: float = 20.0; angle_deg: float = 45.0
      @property vx -> float        # v0 cos θ
      @property vy -> float        # v0 sin θ
      def set_components(self, vx: float, vy: float) -> None   # v0 = hypot, angle = degrees(atan2(vy, vx))
      def set_polar(self, v0: float, angle_deg: float) -> None
      def as_dict(self) -> Dict[str, float]   # keys "x0","y0","v0","angle_deg","vx","vy"

  def parse_number(text: str) -> Optional[float]   # strip, float(); None on failure ("" / "abc" / "1,25")
  def validate_launch(launch: Launch) -> Optional[str]
      # None if fine; "start height can't be below the ground" if y0 < 0; "speed can't be negative" if v0 < 0
  def validate_world(g: float, xmin: float, xmax: float, ymin: float, ymax: float) -> Optional[str]
      # "gravity must be a positive number" if g <= 0
      # "x max must be bigger than x min" / "y max must be bigger than y min"
  ```

- [ ] **Step 1: Write the failing tests**

```python
import math
import pytest
from src.flow_project.launch import Launch, parse_number, validate_launch, validate_world


def test_components_from_polar():
    l = Launch(v0=20.0, angle_deg=45.0)
    assert l.vx == pytest.approx(14.1421, abs=1e-3)
    assert l.vy == pytest.approx(14.1421, abs=1e-3)


def test_set_components_updates_polar():
    l = Launch(v0=20.0, angle_deg=45.0)
    l.set_components(20.0, 14.142135)   # push vx up, keep vy: angle drops
    assert l.v0 == pytest.approx(math.hypot(20.0, 14.142135))
    assert l.angle_deg == pytest.approx(math.degrees(math.atan2(14.142135, 20.0)))
    assert l.vx == pytest.approx(20.0) and l.vy == pytest.approx(14.142135)


def test_round_trip_is_stable():
    l = Launch(v0=17.3, angle_deg=28.0)
    l.set_components(l.vx, l.vy)
    assert l.v0 == pytest.approx(17.3, abs=1e-9) and l.angle_deg == pytest.approx(28.0, abs=1e-9)


def test_negative_components_give_angles_outside_0_90():
    l = Launch(); l.set_components(-10.0, 10.0)
    assert l.angle_deg == pytest.approx(135.0)
    l.set_components(10.0, -5.0)
    assert l.angle_deg < 0


def test_as_dict_keys():
    assert set(Launch().as_dict()) == {"x0", "y0", "v0", "angle_deg", "vx", "vy"}


@pytest.mark.parametrize("text,expected", [("1.25", 1.25), (" 2 ", 2.0), ("-3", -3.0), ("", None), ("abc", None), ("1,25", None)])
def test_parse_number(text, expected):
    assert parse_number(text) == expected


def test_validate_messages():
    assert validate_launch(Launch()) is None
    assert validate_launch(Launch(y0=-3.0)) == "start height can't be below the ground"
    assert validate_launch(Launch(v0=-1.0)) == "speed can't be negative"
    assert validate_world(9.8, 0, 45, 0, 15) is None
    assert validate_world(0.0, 0, 45, 0, 15) == "gravity must be a positive number"
    assert validate_world(9.8, 45, 45, 0, 15) == "x max must be bigger than x min"
    assert validate_world(9.8, 0, 45, 20, 15) == "y max must be bigger than y min"
```

- [ ] **Step 2: Run to verify they fail** — `.venv/bin/pytest tests/test_launch.py -q` → `ModuleNotFoundError`.
- [ ] **Step 3: Implement `src/flow_project/launch.py`.** The two `# PHYSICS:` lines are the component split and the hypot/atan2 recombination.
- [ ] **Step 4: Run to verify they pass** — all pass.
- [ ] **Step 5: Commit** — `git add src/flow_project/launch.py tests/test_launch.py && git commit -m "Add Launch settings with linked vx/vy and v0/θ, plus validation"`

---

### Task 3: `Playback`, a shared clock for two flights (replaces `Player`)

**Files:**
- Rewrite: `src/flow_project/player.py`
- Rewrite: `tests/test_player.py` (delete the old `Player` tests)

**Interfaces:**
- Consumes: `Flight` (Task 1).
- Produces:
  ```python
  class PathState(NamedTuple): x: float; y: float; vx: float; vy: float; speed: float; t: float; landed: bool

  class Playback:
      def __init__(self, flights: List[Flight], frame_dt: float = 0.02,
                   pause_interval: float = 0.5, auto_pause: bool = False, visible: Optional[List[bool]] = None)
      flights: List[Flight]; t: float; paused: bool; visible: List[bool]
      frame_dt: float; pause_interval: float; auto_pause: bool
      marks: List[Tuple[int, float, float, float]]   # (path index, x, y, t) in order added
      @property end_time -> float      # longest flight_time among VISIBLE flights (0 if none)
      @property finished -> bool       # t >= end_time - 1e-9
      def state(self, i: int) -> PathState   # sample nearest min(t, flight_time_i); landed = t >= flight_time_i
      def advance(self) -> None        # +frame_dt; no-op if paused or finished; stops exactly on the next k*pause_interval when auto_pause; pauses (with marks) when it reaches end_time
      def toggle_pause(self) -> None   # pause adds marks; resume adds none; resume when finished restarts from 0
      def step_forward(self) -> None   # to the next multiple of pause_interval (clamped), pause, marks
      def jump_to(self, t: float) -> None   # clamp to [0, end_time], pause, marks
      def scrub_to(self, t: float) -> None  # clamp, pause, NO marks
      def clear_marks(self) -> None
      def restart(self) -> None        # t = 0, playing, marks kept
      def set_flights(self, flights, visible=None) -> None   # new flights, restart
  ```
  Marks: one per visible path whose flight_time ≥ t (a landed path gets no new mark), skipped if that path already has a mark at this t. `t` is a continuous float, never snapped to a sample (this is what fixes the coarse-DT freeze).

- [ ] **Step 1: Write the failing tests** (replace the file's contents)

```python
import pytest
from src.flow_project.player import Playback, PathState
from src.flow_project.projectile import simulate


@pytest.fixture
def two():
    return [simulate(20.0, 45.0), simulate(20.0, 30.0, start_height=5.0)]


def test_starts_at_zero_playing(two):
    p = Playback(two)
    assert p.t == 0.0 and not p.paused and not p.finished
    assert p.end_time == pytest.approx(max(f.flight_time for f in two))
    assert isinstance(p.state(0), PathState) and p.state(0).speed == pytest.approx(20.0)


def test_advance_moves_frame_dt(two):
    p = Playback(two, frame_dt=0.02)
    p.advance(); p.advance()
    assert p.t == pytest.approx(0.04)
    assert p.state(0).t == pytest.approx(0.04, abs=0.0005)


def test_no_auto_pause_by_default_runs_to_end(two):
    p = Playback(two, frame_dt=0.02)
    for _ in range(10000):
        p.advance()
    assert p.finished and p.paused and p.t == pytest.approx(p.end_time)


def test_auto_pause_exact_multiples(two):
    p = Playback(two, frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    stops = []
    for _ in range(10000):
        if p.paused:
            stops.append(p.t)
            if p.finished:
                break
            p.toggle_pause()
        p.advance()
    assert stops[:4] == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert all(b > a for a, b in zip(stops, stops[1:]))


def test_pause_marks_each_visible_path(two):
    p = Playback(two)
    for _ in range(10):
        p.advance()
    p.toggle_pause()
    assert [m[0] for m in p.marks] == [0, 1]
    assert p.marks[0][3] == pytest.approx(p.t)
    p.toggle_pause()
    assert not p.paused and len(p.marks) == 2


def test_hidden_path_gets_no_mark(two):
    p = Playback(two, visible=[True, False])
    p.jump_to(1.0)
    assert [m[0] for m in p.marks] == [0]
    assert p.end_time == pytest.approx(two[0].flight_time)


def test_landed_path_stays_at_landing(two):
    short = min(two, key=lambda f: f.flight_time); i = two.index(short)
    p = Playback(two)
    p.jump_to(short.flight_time + 0.3)
    s = p.state(i)
    assert s.landed and s.y == pytest.approx(0.0, abs=1e-9) and s.x == pytest.approx(short.x[-1])
    assert s.t == pytest.approx(short.flight_time)
    assert [m[0] for m in p.marks] == [1 - i]   # only the still-flying path got a mark


def test_step_jump_scrub(two):
    p = Playback(two, pause_interval=0.5)
    p.step_forward(); assert p.paused and p.t == pytest.approx(0.5)
    p.jump_to(1.23); assert p.t == pytest.approx(1.23) and p.marks[-1][3] == pytest.approx(1.23)
    n = len(p.marks)
    p.scrub_to(2.0); assert p.t == pytest.approx(2.0) and p.paused and len(p.marks) == n
    p.jump_to(99.0); assert p.finished
    p.jump_to(-1.0); assert p.t == 0.0


def test_no_duplicate_marks_same_time(two):
    p = Playback(two)
    p.jump_to(1.0); p.toggle_pause(); p.toggle_pause()
    assert len(p.marks) == 2


def test_resume_after_end_restarts_and_clear_marks(two):
    p = Playback(two)
    p.jump_to(99.0); p.toggle_pause()
    assert p.t == 0.0 and not p.paused
    p.jump_to(0.5); p.clear_marks(); assert p.marks == []


def test_coarse_dt_reaches_end():
    p = Playback([simulate(20.0, 45.0, dt=0.05)], frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    for _ in range(10000):
        if p.paused and not p.finished:
            p.toggle_pause()
        p.advance()
    assert p.finished


def test_set_flights_restarts(two):
    p = Playback(two); p.jump_to(1.0)
    p.set_flights([simulate(10.0, 60.0)])
    assert p.t == 0.0 and not p.paused and len(p.visible) == 1


def test_zero_length_flight_is_finished():
    p = Playback([simulate(20.0, 0.0)])
    assert p.finished and p.state(0).landed
```

- [ ] **Step 2: Run to verify they fail** — `.venv/bin/pytest tests/test_player.py -q` → `ImportError: cannot import name 'Playback'`.
- [ ] **Step 3: Rewrite `src/flow_project/player.py`** (remove `Player`; keep `next_pause_time` for auto-pause arithmetic). `advance`: `target = t + frame_dt`; if auto_pause and `target >= next_stop - 1e-9`: `target = next_stop`, pause after moving, `next_stop += pause_interval`; clamp to `end_time`; pause at end. `_pause_here()` adds marks per the rule above and recomputes `next_stop = next_pause_time(t, pause_interval)` when not given.
- [ ] **Step 4: Run to verify they pass.** Also run `.venv/bin/pytest -q` and note which other test files now fail (expected: `tests/test_animate.py`, `tests/test_ball_no_air.py` import `Player`; they are rewritten in Tasks 4 and 6). Do not fix them here.
- [ ] **Step 5: Commit** — `git add src/flow_project/player.py tests/test_player.py && git commit -m "Replace Player with Playback: shared clock for two flights"`

---

### Task 4: `FlightPlot` draws a `Playback` (replaces `FlightAnimation`)

**Files:**
- Rewrite: `src/flow_project/animate.py`
- Rewrite: `tests/test_animate.py`

**Interfaces:**
- Consumes: `Flight`, `exact_position` (Task 1), `Launch` (Task 2), `Playback`, `PathState` (Task 3).
- Produces:
  ```python
  PATH_COLORS = ["#0b6e8e", "#c2491d"]; SPEED_COLOR = "#4a3e8a"; MARK_COLOR = "#8a8f98"; ARROW_FRACTION = 0.15

  def auto_limits(flights: List[Flight]) -> Tuple[float, float, float, float]  # (xmin, xmax, ymin, ymax) per spec rules
  def label_side(x: float, xmin: float, xmax: float) -> str   # "left" if x > xmin + 0.75*(xmax-xmin) else "right"
  def format_readout_table(states: List[Optional[PathState]], flights: List[Optional[Flight]], gaps: List[Optional[float]]) -> str
      # header "          A        B"; rows x, y, vx, vy, v (1 dp), range, max h, flight (1/1/2 dp), "sim−eq" (3 dp); "—" where None

  class FlightPlot:
      def __init__(self, ax, playback: Playback, launches: List[Launch], g: float)
      show_arrows: bool = True; show_labels: bool = True; show_cross: bool = True
      balls, trails, crosses, vx_arrows, vy_arrows, label_texts: List[...]   # one per path (label_texts[i] is a 2-tuple of Text)
      marks_scatter; clock_text
      def set_flights(self, playback: Playback, launches: List[Launch], g: float) -> None  # rebind after Play
      def set_limits(self, xmin, xmax, ymin, ymax) -> None   # also recomputes arrow scales
      def gap(self, i: int) -> float   # distance between state(i) and exact_position at state(i).t
      def draw(self) -> None           # redraw everything from playback; hidden paths invisible
  ```
  Text formats: label line 1 `"vx {vx:.1f}  vy {vy:+.1f}"`, line 2 `"v {speed:.1f}"`; clock `"t = {t:.2f} s"` + `" (paused)"`; mark label `"{t:.1f}s"`. Arrows use per-axis scales so 1 m/s is the same pixel length both ways, with the fastest visible speed = `ARROW_FRACTION` of the plot width (carry the v1 code over).

- [ ] **Step 1: Write the failing tests** (replace the file)

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from src.flow_project.animate import FlightPlot, auto_limits, format_readout_table, label_side
from src.flow_project.launch import Launch
from src.flow_project.player import Playback
from src.flow_project.projectile import simulate


def test_auto_limits_fit_both_flights():
    fl = [simulate(20.0, 45.0), simulate(20.0, 30.0, start_height=5.0)]
    xmin, xmax, ymin, ymax = auto_limits(fl)
    assert xmin == 0 and ymin == 0
    assert xmax == pytest.approx(1.1 * max(f.x.max() for f in fl))
    assert ymax == pytest.approx(1.25 * max(f.y.max() for f in fl))


def test_auto_limits_negative_x():
    xmin, xmax, _, _ = auto_limits([simulate(20.0, 135.0)])
    assert xmin == pytest.approx(1.1 * simulate(20.0, 135.0).x.min()) and xmax == 0


def test_auto_limits_never_collapse():
    xmin, xmax, ymin, ymax = auto_limits([simulate(20.0, 90.0)])
    assert xmax - xmin >= 1.0 and xmin < 0 < xmax
    xmin, xmax, ymin, ymax = auto_limits([simulate(20.0, 0.0)])
    assert xmax - xmin >= 1.0 and ymax - ymin >= 1.0


def test_label_side_uses_visible_range():
    assert label_side(10.0, 0.0, 100.0) == "right"
    assert label_side(80.0, 0.0, 100.0) == "left"
    assert label_side(-5.0, -40.0, 0.0) == "left"


def test_format_readout_table():
    fl = [simulate(20.0, 45.0), None]
    p = Playback([fl[0]]); p.jump_to(1.0)
    text = format_readout_table([p.state(0), None], fl, [0.0004, None])
    lines = text.splitlines()
    assert "A" in lines[0] and "B" in lines[0]
    assert any(l.startswith("vx") and "14.1" in l and "—" in l for l in lines)
    assert any(l.startswith("sim−eq") and "0.000" in l for l in lines)


@pytest.fixture
def plot():
    launches = [Launch(), Launch(y0=5.0, angle_deg=30.0)]
    fl = [simulate(l.v0, l.angle_deg, start_height=l.y0, start_x=l.x0) for l in launches]
    pb = Playback(fl)
    fig, ax = plt.subplots(figsize=(8, 6))
    fp = FlightPlot(ax, pb, launches, 9.8)
    fp.set_limits(*auto_limits(fl))
    return fp, pb


def test_two_balls_drawn_at_their_positions(plot):
    fp, pb = plot
    pb.jump_to(0.8); fp.draw()
    for i in range(2):
        x, y = fp.balls[i].get_data()
        assert float(x[0]) == pytest.approx(pb.state(i).x) and float(y[0]) == pytest.approx(pb.state(i).y)
    assert "vx 14.1" in fp.label_texts[0][0].get_text()
    assert fp.clock_text.get_text() == "t = 0.80 s (paused)"


def test_hidden_path_is_invisible(plot):
    fp, pb = plot
    pb.visible[1] = False; fp.draw()
    assert not fp.balls[1].get_visible() and not fp.trails[1].get_visible()
    assert fp.balls[0].get_visible()


def test_cross_matches_equation_and_gap_is_tiny(plot):
    fp, pb = plot
    pb.jump_to(1.2); fp.draw()
    assert fp.gap(0) < 0.01 * abs(pb.state(0).x) + 1e-6
    cx, cy = fp.crosses[0].get_data()
    assert float(cx[0]) == pytest.approx(pb.state(0).x, abs=0.05)


def test_landed_ball_stays_put(plot):
    fp, pb = plot
    short = min(range(2), key=lambda i: pb.flights[i].flight_time)
    pb.jump_to(pb.end_time); fp.draw()
    x, y = fp.balls[short].get_data()
    assert float(y[0]) == pytest.approx(0.0, abs=1e-9)
    assert float(x[0]) == pytest.approx(pb.flights[short].x[-1])


def test_arrows_equal_on_screen_for_equal_components(plot):
    fp, pb = plot
    fp.draw()
    to_px = fp.ax.transData.transform
    a = fp.vx_arrows[0]; b = fp.vy_arrows[0]
    vx_len = abs(to_px(a.xy)[0] - to_px(a.xyann)[0]); vy_len = abs(to_px(b.xy)[1] - to_px(b.xyann)[1])
    assert vx_len == pytest.approx(vy_len, rel=0.02) and vx_len > 20


def test_toggles_hide_arrows_and_labels(plot):
    fp, pb = plot
    fp.show_arrows = False; fp.show_labels = False; fp.draw()
    assert not fp.vx_arrows[0].get_visible() and not fp.label_texts[0][0].get_visible()


def test_marks_drawn_with_time_labels(plot):
    fp, pb = plot
    pb.jump_to(0.5); pb.toggle_pause(); pb.jump_to(1.0); fp.draw()
    assert len(fp.marks_scatter.get_offsets()) == 4
    assert any(t.get_text() == "0.5s" for t in fp.mark_labels)


def test_set_limits_applied(plot):
    fp, _ = plot
    fp.set_limits(-5, 50, 0, 30)
    assert fp.ax.get_xlim() == (-5, 50) and fp.ax.get_ylim() == (0, 30)
```

- [ ] **Step 2: Run to verify they fail** — `ImportError` for `FlightPlot`/`auto_limits`.
- [ ] **Step 3: Rewrite `src/flow_project/animate.py`.** Keep the per-axis arrow scaling and label-offset logic from v1 (`offset = 0.03*width + |vx|*scale_x`). `FlightPlot` creates artists for exactly `len(playback.flights)` paths and recreates them in `set_flights` if the count changes. `draw()` never calls `playback.advance()`; the window does that.
- [ ] **Step 4: Run to verify they pass** — `.venv/bin/pytest tests/test_animate.py -q` all pass.
- [ ] **Step 5: Commit** — `git add src/flow_project/animate.py tests/test_animate.py && git commit -m "Replace FlightAnimation with FlightPlot: two paths, equation cross, toggles"`

---

### Task 5: `LaunchWindow`, the widgets

**Files:**
- Create: `src/flow_project/launch_window.py`
- Test: `tests/test_launch_window.py`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  ```python
  class LaunchWindow:
      def __init__(self, launches: List[Launch], g: float = 9.8, dt: float = 0.001, frame_dt: float = 0.02,
                   pause_interval: float = 0.5, auto_pause: bool = False, playback_speed: float = 0.5,
                   path_b_on: bool = True, title: str = "Ball with no air")
      fig; ax; plot: FlightPlot; playback: Playback; launches: List[Launch]; g: float
      boxes: Dict[Tuple[int, str], TextBox]      # (path index, key in "x0","y0","v0","angle_deg","vx","vy")
      g_box, xmin_box, xmax_box, ymin_box, ymax_box, interval_box, jump_box: TextBox
      play_button, step_button, clear_button, autofit_button, go_button: Button
      preset_buttons: Dict[str, Button]           # "Earth","Moon","Mars","Jupiter"
      path_b_check, auto_pause_check, show_check: CheckButtons   # show_check labels ["arrows", "numbers", "equation ✕"]
      speed_radio: RadioButtons                   # ["0.25×","0.5×","1×"]
      slider: Slider                              # 0..1 of end_time
      status_text, readout_text: Text
      equation_pieces: Dict[str, Text]            # clickable numbers: "x0","y0","v0","angle_deg","g"
      selected_path: int                          # 0 or 1, for the banner
      axes_edited: bool                           # True once the student typed in an axis box

      def on_box_submit(self, path: int, key: str, text: str) -> None   # updates Launch, rewrites the 6 boxes of that path, refreshes banner; bad number → status
      def on_play(self, event=None) -> None      # validate → build flights → playback.set_flights → plot.set_flights → (auto-fit if not axes_edited) → status cleared; else status message, old flight untouched
      def on_step(self, event=None); on_jump(self, text: str); on_scrub(self, value: float); on_clear(self, event=None); on_autofit(self, event=None)
      def on_key(self, event) -> None            # " " → play/pause (same as on_play when no flight yet), "right" → step; ignored while any TextBox captures keystrokes
      def on_pick(self, event) -> None           # equation piece → boxes[(selected_path, key)].begin_typing() (g → g_box), highlight
      def select_path(self, i: int) -> None      # A/B banner buttons
      def apply_preset(self, name: str) -> None  # fills g_box only; applied on Play
      def on_axis_submit(self, text: str = "") -> None   # reads the four axis boxes, validates, applies, sets axes_edited
      def set_path_b(self, on: bool) -> None     # checkbox handler; playback.visible[1] = on
      def tick(self, frame: int) -> None         # playback.advance(); plot.draw(); readout; slider; FuncAnimation callback
      def run(self) -> None                      # FuncAnimation(interval = frame_dt/speed*1000) + plt.show()
  ```
  Layout in figure fractions (fig 13 × 8.2 in): banner y 0.93–0.99 full width; plot axes [0.05, 0.27, 0.60, 0.62]; slider [0.07, 0.21, 0.56, 0.02]; playback bar y 0.12–0.19 across x 0.05–0.66; status text at (0.05, 0.08); side panel x 0.70–0.98: Launch grid y 0.56–0.90 (two columns at x 0.80 and 0.90, rows 0.045 apart, labels at 0.70), World & view y 0.30–0.52, Readout text y 0.03–0.27. Group titles as bold `fig.text`.

- [ ] **Step 1: Write the failing tests**

```python
import matplotlib
matplotlib.use("Agg")
import pytest
from matplotlib.backend_bases import MouseEvent, PickEvent

from src.flow_project.launch import Launch
from src.flow_project.launch_window import LaunchWindow


class Key:
    def __init__(self, key): self.key = key; self.inaxes = None


@pytest.fixture
def win():
    return LaunchWindow([Launch(), Launch(y0=5.0, angle_deg=30.0)])


def test_window_builds_with_two_paths_and_defaults(win):
    assert len(win.playback.flights) == 2
    assert win.boxes[(0, "v0")].text == "20" and win.boxes[(1, "y0")].text == "5"
    assert win.g_box.text == "9.8" and not win.playback.paused
    assert win.boxes[(0, "vx")].text == "14.1"


def test_submitting_vx_rewrites_v0_and_angle(win):
    win.on_box_submit(0, "vx", "20")
    assert win.boxes[(0, "angle_deg")].text == "35.3"
    assert win.boxes[(0, "v0")].text == "24.5"
    assert win.launches[0].vx == pytest.approx(20.0)


def test_submitting_angle_rewrites_components(win):
    win.on_box_submit(0, "angle_deg", "60")
    assert win.boxes[(0, "vx")].text == "10.0" and win.boxes[(0, "vy")].text == "17.3"


def test_changes_apply_only_on_play(win):
    win.on_box_submit(0, "v0", "30")
    assert win.playback.flights[0].speed[0] == pytest.approx(20.0)
    win.on_play()
    assert win.playback.flights[0].speed[0] == pytest.approx(30.0) and win.playback.t == 0.0


def test_tick_advances_and_updates_readout_and_slider(win):
    for i in range(5): win.tick(i)
    assert win.playback.t == pytest.approx(0.10)
    assert "t = 0.10 s" in win.plot.clock_text.get_text()
    assert "vx" in win.readout_text.get_text()
    assert win.slider.val == pytest.approx(0.10 / win.playback.end_time, abs=1e-3)


def test_space_toggles_and_right_steps(win):
    win.on_key(Key(" ")); assert win.playback.paused and len(win.playback.marks) == 2
    win.on_key(Key(" ")); assert not win.playback.paused
    win.on_key(Key("right")); assert win.playback.paused and win.playback.t == pytest.approx(0.5)


def test_space_ignored_while_typing(win):
    win.boxes[(0, "v0")].begin_typing()
    win.on_key(Key(" "))
    assert not win.playback.paused
    win.boxes[(0, "v0")].stop_typing()


def test_enter_in_box_ends_typing(win):
    box = win.boxes[(0, "vx")]; box.begin_typing(); box.set_val("15")
    box._observers.process("submit", box.text)   # what Enter does
    assert not box.capturekeystrokes


def test_jump_box_and_go(win):
    win.on_jump("1.25")
    assert win.playback.t == pytest.approx(1.25) and win.playback.paused
    win.on_jump("abc"); assert win.playback.t == pytest.approx(1.25)
    assert "number" in win.status_text.get_text()


def test_bad_input_shows_status_and_keeps_old_flight(win):
    win.on_jump("1.0")
    win.g_box.set_val("0")
    win.on_play()
    assert win.status_text.get_text() == "gravity must be a positive number"
    assert win.playback.t == pytest.approx(1.0) and win.playback.paused
    win.g_box.set_val("9.8"); win.on_play()
    assert win.status_text.get_text() == ""


def test_preset_fills_g_box(win):
    win.apply_preset("Moon")
    assert win.g_box.text == "1.6" and win.g == pytest.approx(9.8)   # not applied until Play
    win.on_play(); assert win.g == pytest.approx(1.6)


def test_axis_boxes_and_autofit(win):
    win.xmax_box.set_val("100"); win.on_axis_submit()
    assert win.axes_edited and win.ax.get_xlim()[1] == pytest.approx(100)
    win.on_play(); assert win.ax.get_xlim()[1] == pytest.approx(100)   # respected
    win.on_autofit(); assert win.ax.get_xlim()[1] < 100 and not win.axes_edited


def test_path_b_checkbox_hides_second_ball(win):
    win.set_path_b(False); win.on_play(); win.tick(0)
    assert not win.plot.balls[1].get_visible() and win.playback.visible == [True, False]


def test_equation_click_begins_typing_in_matching_box(win):
    ev = PickEvent("pick_event", win.fig.canvas, MouseEvent("button_press_event", win.fig.canvas, 0, 0), win.equation_pieces["v0"])
    win.on_pick(ev)
    assert win.boxes[(0, "v0")].capturekeystrokes
    win.boxes[(0, "v0")].stop_typing()
    win.select_path(1)
    assert "30" in win.equation_pieces["angle_deg"].get_text()


def test_scrub_pauses_without_marks(win):
    win.on_scrub(0.5)
    assert win.playback.paused and win.playback.marks == []
```

- [ ] **Step 2: Run to verify they fail** — `ModuleNotFoundError`.
- [ ] **Step 3: Implement `src/flow_project/launch_window.py`.** Box text formatting: one decimal for v0/vx/vy/angle, `"{:g}"` for x0/y0/g/axes. Guard every TextBox `on_submit` handler against the re-entrant submit from `stop_typing()` (a `self._submitting` flag) and call `stop_typing()` inside the handler so Enter ends typing. `on_key` returns early if `any(b.capturekeystrokes for b in all_boxes)`. Equation pieces: `fig.text` artists laid left-to-right; after each `fig.canvas.draw()` use `get_window_extent()` widths to place the next piece; numbers get `picker=True` and a rounded `bbox`. Hidden path B column boxes get `color` greyed via `box.ax.set_facecolor`.
- [ ] **Step 4: Run to verify they pass** — `.venv/bin/pytest tests/test_launch_window.py -q`.
- [ ] **Step 5: Commit** — `git add src/flow_project/launch_window.py tests/test_launch_window.py && git commit -m "Add LaunchWindow: matplotlib-widget UI with equation banner and two paths"`

---

### Task 6: Runnable file, docs, and the real-window check

**Files:**
- Rewrite: `simulations/ball_no_air/ball_no_air.py`
- Rewrite: `tests/test_ball_no_air.py`
- Modify: `simulations/ball_no_air/README.md`, `README.md`

**Interfaces:**
- Produces (top of `ball_no_air.py`, all with comments):
  ```python
  PATH_A = dict(x0=0.0, y0=0.0, v0=20.0, angle_deg=45.0)
  PATH_B = dict(x0=0.0, y0=5.0, v0=20.0, angle_deg=30.0)
  PATH_B_ON = True
  GRAVITY = 9.8
  DT = 0.001; FRAME_DT = 0.02; PAUSE_INTERVAL = 0.5; AUTO_PAUSE = False; PLAYBACK_SPEED = 0.5
  def build_window() -> LaunchWindow
  def main(show: bool = True) -> LaunchWindow   # calls .run() only when show
  ```

- [ ] **Step 1: Write the failing tests** (replace the file)

```python
import matplotlib
matplotlib.use("Agg")
import pytest
from simulations.ball_no_air import ball_no_air as sim


def test_settings_are_sensible():
    for p in (sim.PATH_A, sim.PATH_B):
        assert set(p) == {"x0", "y0", "v0", "angle_deg"} and p["y0"] >= 0 and p["v0"] >= 0
    assert sim.GRAVITY > 0 and sim.DT > 0 and sim.FRAME_DT > 0 and sim.PAUSE_INTERVAL > 0
    assert sim.PLAYBACK_SPEED in (0.25, 0.5, 1.0) and isinstance(sim.AUTO_PAUSE, bool)


def test_build_window_uses_settings():
    w = sim.build_window()
    assert w.launches[0].v0 == pytest.approx(sim.PATH_A["v0"])
    assert w.launches[1].y0 == pytest.approx(sim.PATH_B["y0"])
    assert w.g == pytest.approx(sim.GRAVITY) and w.playback.auto_pause is sim.AUTO_PAUSE


def test_main_without_show_returns_window():
    w = sim.main(show=False)
    w.tick(0)
    assert w.playback.t > 0
```

- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Rewrite `ball_no_air.py`** (docstring explains the window and keys; settings block; `build_window`, `main`). `main.py` needs no change.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_ball_no_air.py tests/test_main.py -q` → pass. Then `make test` → everything passes.
- [ ] **Step 5: Look at it:** `make run`. Check against the mockup: banner readable, nothing overlapping, Play runs without pausing, space pauses, Enter in vx then space resumes, Moon preset + Play, θ = 90 + Auto-fit, Path B off, slider scrub. Fix layout issues found, re-run `make test`.
- [ ] **Step 6: Docs.** `simulations/ball_no_air/README.md`: controls table (Play/space, right arrow, jump box, slider, auto-pause box, presets, axis boxes, toggles), settings table for the new constants, "where the physics is". Root `README.md`: one line that the window has on-screen controls.
- [ ] **Step 7: Commit** — `git add simulations README.md tests/test_ball_no_air.py && git commit -m "ball_no_air v2: on-screen controls, equation banner, two paths"`

---

### Task 7: Final review

- [ ] `make test` green.
- [ ] Whole-branch review per `superpowers:requesting-code-review` against the spec (range: merge-base with `main` to HEAD). Fix Critical/Important with tests; ledger minors.
- [ ] Stop. Do not merge; the student's teacher approves checkpoints.
