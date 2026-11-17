"""The launch window: boxes, buttons, the equation banner and the plot.

This file is only "wiring". It places matplotlib widgets on one window and
passes every click and key press on to the pieces that make the decisions:
  - launch.py     the numbers for each path (and the vx/vy <-> v0/θ link)
  - projectile.py the physics (runs a whole flight in tiny time slices)
  - player.py     the clock: playing, pausing, stepping, jumping, markers
  - animate.py    drawing the balls, trails, arrows and numbers

New numbers typed into the boxes are used the next time Play is pressed,
never in the middle of a flight. The Play button says "Launch" when there are
new numbers waiting.
"""

import dataclasses
import time
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, CheckButtons, RadioButtons, Slider, TextBox

from src.flow_project.animate import PATH_COLORS, FlightPlot, auto_limits, format_readout_table
from src.flow_project.launch import (
    Launch,
    parse_number,
    validate_flight_size,
    validate_launch,
    validate_world,
)
from src.flow_project.player import Playback
from src.flow_project.projectile import simulate

# ---------------------------------------------------------------------------
# Settings for how the window looks
# ---------------------------------------------------------------------------
FIG_SIZE = (13, 8.2)  # inches; about 1300 x 820 pixels
BOX_COLOR = "0.95"  # normal text box
HIGHLIGHT_COLOR = "#fff1c2"  # box picked by clicking the equation
OFF_COLOR = "#dcdcdc"  # Path B boxes while Path B is switched off
STATUS_COLOR = "#c2491d"  # error messages
GRAVITY_PRESETS = {"Earth": 9.8, "Moon": 1.6, "Mars": 3.7, "Jupiter": 24.8}
SPEEDS = {"0.25×": 0.25, "0.5×": 0.5, "1×": 1.0}  # playback speed choices

# The six boxes for each path, top to bottom, and their row labels
LAUNCH_KEYS = ["x0", "y0", "v0", "angle_deg", "vx", "vy"]
ROW_LABELS = {
    "x0": r"$x_0$  (m)",
    "y0": r"$y_0$  (m)",
    "v0": r"$v_0$  (m/s)",
    "angle_deg": r"$\theta$  (°)",
    "vx": r"$v_x$  (m/s)",
    "vy": r"$v_y$  (m/s)",
}
PATH_NAMES = ["A", "B"]

# Where things go, as fractions of the window: [left, bottom, width, height]
PLOT_RECT = [0.06, 0.30, 0.60, 0.60]
SLIDER_RECT = [0.08, 0.215, 0.56, 0.025]
BANNER_Y = 0.955
SIDE_X = 0.70  # left edge of the side panel
COL_X = [0.775, 0.875]  # left edge of the Path A and Path B box columns
BOX_W, BOX_H = 0.075, 0.032
LAUNCH_TOP = 0.855  # y of the first launch row
ROW_STEP = 0.042  # gap between launch rows


class QuietTextBox(TextBox):
    """A matplotlib TextBox that doesn't redraw the window when it has nothing to do.

    matplotlib's own box redraws the whole window every time you click
    anywhere outside it, even if you weren't typing in it. With 21 boxes that
    made every click slow.
    """

    def stop_typing(self):
        if not self.capturekeystrokes:
            return
        super().stop_typing()


def disable_matplotlib_shortcuts() -> None:
    """Turn off matplotlib's single-key shortcuts (q = quit, l = log scale, s = save...).

    This window has its own controls, and a stray key press could otherwise
    close the window or break the plot.
    """
    for name in list(matplotlib.rcParams):
        if name.startswith("keymap."):
            matplotlib.rcParams[name] = []


def _fmt(value: float) -> str:
    """Short form for a number someone typed: 20, 14.142, -3."""
    value = round(value, 3)
    if abs(value) < 5e-4:
        value = 0.0
    return "{:g}".format(value)


class LaunchWindow:
    """One window: equation banner, plot, playback bar and side panel."""

    def __init__(
        self,
        launches: List[Launch],
        g: float = 9.8,
        dt: float = 0.001,
        frame_dt: float = 0.02,
        pause_interval: float = 0.5,
        auto_pause: bool = False,
        playback_speed: float = 0.5,
        path_b_on: bool = True,
        title: str = "Ball with no air",
    ) -> None:
        self.launches = [dataclasses.replace(launch) for launch in launches]
        self.g = g
        self.dt = dt
        self.playback_speed = playback_speed
        self.path_b_on = path_b_on and len(self.launches) > 1
        self.selected_path = 0
        self.axes_edited = False
        self._dirty = False  # True when typed numbers are waiting for Play
        self._submitting = False  # guards against a box reporting twice
        self._pending_focus: Optional[TextBox] = None
        self._written: Dict[int, str] = {}  # what the program last wrote in each box
        self._source = ["polar"] * len(self.launches)  # which velocity pair was typed last
        self._animation = None
        self.clock = time.perf_counter  # the computer's stopwatch (tests swap in a fake one)
        self._last_tick: Optional[float] = None

        self.fig = plt.figure(figsize=FIG_SIZE)
        if self.fig.canvas.manager is not None:
            self.fig.canvas.manager.set_window_title(title)
        self.ax = self.fig.add_axes(PLOT_RECT)

        flights = self._build_flights(self.launches, g)
        self.playback = Playback(
            flights, frame_dt=frame_dt, pause_interval=pause_interval,
            auto_pause=auto_pause, visible=self._visible(),
        )
        self.plot = FlightPlot(self.ax, self.playback, self.launches_snapshot(), g)

        self._build_banner()
        self._build_playback_bar(pause_interval, auto_pause)
        self._build_side_panel()

        self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        self.fig.canvas.mpl_connect("pick_event", self.on_pick)
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)

        self._apply_auto_limits()
        self._refresh_banner()
        self._refresh()

    # ======================================================================
    # Building the window
    # ======================================================================

    def _box(self, rect, text: str, label: str = "") -> TextBox:
        box = QuietTextBox(self.fig.add_axes(rect), label, initial=text, color=BOX_COLOR, hovercolor="1")
        self._written[id(box)] = text
        return box

    def _on_submit(self, box: TextBox, handler: Callable[[str], None]) -> None:
        """Run handler when Enter is pressed (or the box loses focus).

        Pressing Enter does not take the cursor out of a box on its own, so the
        next space would be typed into the box. We end typing here so the
        space bar works straight away. stop_typing() reports the text a second
        time; the _submitting flag ignores that echo.
        """

        def wrapped(text: str) -> None:
            if self._submitting:
                return
            self._submitting = True
            try:
                box.stop_typing()
                handler(text)
            finally:
                self._submitting = False

        box.on_submit(wrapped)

    def _build_banner(self) -> None:
        fig = self.fig
        number_box = dict(boxstyle="round,pad=0.25", fc="#f3f1ea", ec="#8a8f98", ls="--")
        math_style = dict(fontsize=15, va="center")
        number_style = dict(fontsize=13, va="center", family="monospace", bbox=number_box, picker=True)
        # The equation, split into fixed pieces ("T") and clickable numbers ("N")
        layout = [
            ("T", r"$\vec{r}\,(t)\ =\ ($"), ("N", "x0"), ("T", r"$+\ ($"), ("N", "v0"),
            ("T", r"$\cos$"), ("N", "angle_deg"), ("T", r"$)\,t\,)\ \hat{\imath}\ \ +\ \ ($"),
            ("N", "y0"), ("T", r"$+\ ($"), ("N", "v0"), ("T", r"$\sin$"), ("N", "angle_deg"),
            ("T", r"$)\,t\ -\ \frac{1}{2}$"), ("N", "g"), ("T", r"$t^2\,)\ \hat{\jmath}$"),
        ]
        self._banner: List[Tuple[object, Optional[str]]] = []
        self.equation_pieces: Dict[str, object] = {}
        self._piece_key: Dict[int, str] = {}
        for kind, value in layout:
            if kind == "T":
                text = fig.text(0, BANNER_Y, value, **math_style)
                self._banner.append((text, None))
            else:
                text = fig.text(0, BANNER_Y, "", **number_style)
                self._banner.append((text, value))
                self._piece_key[id(text)] = value
                self.equation_pieces.setdefault(value, text)
        fig.text(0.80, BANNER_Y, "equation for path", fontsize=9, va="center", color="0.4")
        self.path_buttons = []
        for i in range(len(self.launches)):
            button = Button(fig.add_axes([0.905 + 0.035 * i, BANNER_Y - 0.02, 0.03, 0.04]), PATH_NAMES[i])
            button.label.set_color(PATH_COLORS[i])
            button.on_clicked(lambda event, i=i: self.select_path(i))
            self.path_buttons.append(button)
        fig.text(0.02, 0.915, "click a number in the equation to change it", fontsize=8, color="0.45")

    def _build_playback_bar(self, pause_interval: float, auto_pause: bool) -> None:
        fig = self.fig
        self.slider = Slider(fig.add_axes(SLIDER_RECT), "time", 0.0, 1.0, valinit=0.0)
        self.slider.valtext.set_visible(False)
        self.slider.on_changed(self.on_scrub)

        y, h = 0.135, 0.042
        self.play_button = Button(fig.add_axes([0.06, y, 0.075, h]), "Pause")
        self.play_button.on_clicked(self.on_play)
        self.step_button = Button(fig.add_axes([0.14, y, 0.06, h]), "Step ›")
        self.step_button.on_clicked(self.on_step)

        self.auto_pause_check = CheckButtons(fig.add_axes([0.21, y - 0.004, 0.10, 0.05]), ["pause every"], [auto_pause])
        self.auto_pause_check.on_clicked(lambda label: self.set_auto_pause(self.auto_pause_check.get_status()[0]))
        self.interval_box = self._box([0.315, y, 0.04, h], _fmt(pause_interval))
        self._on_submit(self.interval_box, self.on_interval_submit)
        fig.text(0.358, y + h / 2, "s", va="center", fontsize=10)

        self.jump_box = self._box([0.435, y, 0.05, h], "", "jump to t ")
        self._on_submit(self.jump_box, self.on_jump)
        self.go_button = Button(fig.add_axes([0.49, y, 0.035, h]), "Go")
        self.go_button.on_clicked(lambda event: self.on_jump(self.jump_box.text))
        self.clear_button = Button(fig.add_axes([0.54, y, 0.10, h]), "Clear markers")
        self.clear_button.on_clicked(self.on_clear)

        fig.text(0.06, 0.105, "speed", fontsize=9, color="0.4")
        names = list(SPEEDS)
        active = min(range(len(names)), key=lambda k: abs(SPEEDS[names[k]] - self.playback_speed))
        self.speed_radio = RadioButtons(fig.add_axes([0.06, 0.01, 0.08, 0.09]), names, active=active)
        self.speed_radio.on_clicked(self.set_speed)

        self.status_text = fig.text(0.16, 0.08, "", fontsize=10, color=STATUS_COLOR, fontweight="bold")
        fig.text(
            0.16, 0.035,
            "space: play / pause      right arrow: step      Enter: confirm a box",
            fontsize=8.5, color="0.45",
        )

    def _build_side_panel(self) -> None:
        fig = self.fig
        bold = dict(fontsize=11, fontweight="bold")

        # --- Launch: one column of boxes per path ---
        fig.text(SIDE_X, 0.905, "Launch", **bold)
        for i in range(len(self.launches)):
            fig.text(COL_X[i] + BOX_W / 2, 0.895, "Path " + PATH_NAMES[i], ha="center",
                     color=PATH_COLORS[i], fontsize=10, fontweight="bold")
        self.boxes: Dict[Tuple[int, str], TextBox] = {}
        for row, key in enumerate(LAUNCH_KEYS):
            y = LAUNCH_TOP - row * ROW_STEP
            fig.text(SIDE_X, y + BOX_H / 2, ROW_LABELS[key], va="center", fontsize=10)
            for i in range(len(self.launches)):
                box = self._box([COL_X[i], y, BOX_W, BOX_H], "")
                self._on_submit(box, lambda text, i=i, key=key: self.on_box_submit(i, key, text))
                self.boxes[(i, key)] = box
        for i in range(len(self.launches)):
            self._write_path_boxes(i)
        fig.text(SIDE_X, 0.6, r"$v_0$ and $\theta$ are linked to $v_x$ and $v_y$", fontsize=8, color="0.45")
        if len(self.launches) > 1:
            self.path_b_check = CheckButtons(fig.add_axes([0.86, 0.585, 0.12, 0.04]), ["show path B"], [self.path_b_on])
            self.path_b_check.on_clicked(lambda label: self.set_path_b(self.path_b_check.get_status()[0]))
            self._grey_path_b()

        # --- World & view: gravity and the axes ---
        fig.text(SIDE_X, 0.545, "World & view", **bold)
        fig.text(SIDE_X, 0.51 + BOX_H / 2, r"$g$  (m/s²)", va="center", fontsize=10)
        self.g_box = self._box([COL_X[0], 0.51, BOX_W, BOX_H], _fmt(self.g))
        self._on_submit(self.g_box, self.on_g_submit)
        self.preset_buttons: Dict[str, Button] = {}
        for k, name in enumerate(GRAVITY_PRESETS):
            button = Button(fig.add_axes([SIDE_X + k * 0.07, 0.465, 0.065, 0.032]), name)
            button.label.set_fontsize(9)
            button.on_clicked(lambda event, name=name: self.apply_preset(name))
            self.preset_buttons[name] = button
        fig.text(COL_X[0] + BOX_W / 2, 0.453, "min", ha="center", va="top", fontsize=8, color="0.45")
        fig.text(COL_X[1] + BOX_W / 2, 0.453, "max", ha="center", va="top", fontsize=8, color="0.45")
        fig.text(SIDE_X, 0.395 + BOX_H / 2, "x axis (m)", va="center", fontsize=10)
        self.xmin_box = self._box([COL_X[0], 0.395, BOX_W, BOX_H], "")
        self.xmax_box = self._box([COL_X[1], 0.395, BOX_W, BOX_H], "")
        fig.text(SIDE_X, 0.355 + BOX_H / 2, "y axis (m)", va="center", fontsize=10)
        self.ymin_box = self._box([COL_X[0], 0.355, BOX_W, BOX_H], "")
        self.ymax_box = self._box([COL_X[1], 0.355, BOX_W, BOX_H], "")
        for box in (self.xmin_box, self.xmax_box, self.ymin_box, self.ymax_box):
            self._on_submit(box, self.on_axis_submit)
        self.autofit_button = Button(fig.add_axes([COL_X[0], 0.312, 0.175, 0.032]), "Auto-fit axes")
        self.autofit_button.on_clicked(self.on_autofit)
        self.show_check = CheckButtons(
            fig.add_axes([SIDE_X, 0.215, 0.28, 0.085]),
            ["arrows", "numbers on ball", "equation × (where the formula says)"],
            [True, True, True],
        )
        self.show_check.on_clicked(self._on_show_clicked)

        # --- Readout ---
        fig.text(SIDE_X, 0.195, "Readout", **bold)
        self.readout_text = fig.text(SIDE_X, 0.18, "", va="top", fontsize=8.5, family="monospace")

    # ======================================================================
    # Keeping the boxes, banner and plot up to date
    # ======================================================================

    def launches_snapshot(self) -> List[Launch]:
        return [dataclasses.replace(launch) for launch in self.launches]

    def _visible(self) -> List[bool]:
        return [True] + [self.path_b_on] * (len(self.launches) - 1)

    def _write(self, box: TextBox, text: str) -> None:
        """Put text in a box without it reporting back as if someone typed it."""
        # Change the shown text directly: set_val would report it as typed
        # and redraw the whole window for every box.
        box.text_disp.set_text(text)
        box.cursor_index = len(text)
        if not box.capturekeystrokes:
            box.cursor.set_visible(False)
        self._written[id(box)] = text

    def _write_path_boxes(self, i: int) -> None:
        """Show path i's numbers. The pair you typed keeps your digits; the other pair gets 1 decimal."""
        launch = self.launches[i]
        polar = self._source[i] == "polar"
        typed, worked_out = _fmt, "{:.1f}".format
        texts = {
            "x0": _fmt(launch.x0),
            "y0": _fmt(launch.y0),
            "v0": (typed if polar else worked_out)(launch.v0),
            "angle_deg": (typed if polar else worked_out)(launch.angle_deg),
            "vx": (worked_out if polar else typed)(launch.vx),
            "vy": (worked_out if polar else typed)(launch.vy),
        }
        for key, text in texts.items():
            self._write(self.boxes[(i, key)], text)

    def _set_box_color(self, box: TextBox, color: str) -> None:
        box.color = color
        box.ax.set_facecolor(color)

    def _grey_path_b(self) -> None:
        if len(self.launches) < 2:
            return
        for key in LAUNCH_KEYS:
            self._set_box_color(self.boxes[(1, key)], BOX_COLOR if self.path_b_on else OFF_COLOR)

    def _refresh_banner(self) -> None:
        """Put the selected path's numbers into the equation and line the pieces up."""
        launch = self.launches[self.selected_path]
        g_shown = parse_number(self.g_box.text) if hasattr(self, "g_box") else None
        values = {
            "x0": _fmt(round(launch.x0, 2)),
            "y0": _fmt(round(launch.y0, 2)),
            "v0": _fmt(round(launch.v0, 2)),
            "angle_deg": _fmt(round(launch.angle_deg, 2)) + "°",
            "g": _fmt(self.g if g_shown is None else g_shown),
        }
        color = PATH_COLORS[self.selected_path]
        for text, key in self._banner:
            if key is not None:
                text.set_text(values[key])
                text.set_color("black" if key == "g" else color)
        renderer = self.fig.canvas.get_renderer()
        fig_width = self.fig.bbox.width
        x = 0.02 * fig_width
        for text, key in self._banner:
            text.set_x(x / fig_width)
            x += text.get_window_extent(renderer=renderer).width + (9 if key else 3)
        for i, button in enumerate(self.path_buttons):
            on = i == self.selected_path
            button.ax.set_facecolor(HIGHLIGHT_COLOR if on else BOX_COLOR)
            button.color = HIGHLIGHT_COLOR if on else BOX_COLOR

    def _refresh(self) -> None:
        """Redraw the plot, readout, slider and Play button from the current moment."""
        pb = self.playback
        self.plot.draw()
        states = [pb.state(i) if on else None for i, on in enumerate(pb.visible)]
        flights = [f if on else None for f, on in zip(pb.flights, pb.visible)]
        gaps = [self.plot.gap(i) if on else None for i, on in enumerate(pb.visible)]
        self.readout_text.set_text(format_readout_table(states, flights, gaps))
        self.slider.eventson = False
        self.slider.set_val(pb.t / pb.end_time if pb.end_time > 0 else 0.0)
        self.slider.eventson = True
        if self._dirty:
            label = "Launch"
        elif pb.paused:
            label = "Play"
        else:
            label = "Pause"
        self.play_button.label.set_text(label)

    def _redraw_now(self) -> None:
        self._refresh()
        self.fig.canvas.draw_idle()

    def _status(self, message: str) -> None:
        self.status_text.set_text(message)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.play_button.label.set_text("Launch")
        self.fig.canvas.draw_idle()

    def _apply_auto_limits(self) -> None:
        visible = [f for f, on in zip(self.playback.flights, self.playback.visible) if on]
        limits = auto_limits(visible)
        self.plot.set_limits(*limits)
        for box, value in zip((self.xmin_box, self.xmax_box, self.ymin_box, self.ymax_box), limits):
            self._write(box, _fmt(round(value, 1)))

    # ======================================================================
    # Physics happens here, once per Play: build the flights from the boxes
    # ======================================================================

    def _build_flights(self, launches: List[Launch], g: float):
        return [
            simulate(
                speed=abs(launch.v0), angle_deg=launch.angle_deg, g=g,
                start_height=max(launch.y0, 0.0), dt=self.dt, start_x=launch.x0,
            )
            for launch in launches
        ]

    def _launch(self) -> bool:
        """Read every box, check it, and start new flights. False if something's wrong."""
        g = parse_number(self.g_box.text)
        if g is None:
            self._status("gravity: '{}' is not a number".format(self.g_box.text))
            return False
        problem = validate_world(g, 0.0, 1.0, 0.0, 1.0)
        if problem:
            self._status(problem)
            return False
        for i, on in enumerate(self._visible()):
            problem = validate_launch(self.launches[i]) if on else None
            # Even a hidden path is simulated, so its size is always checked.
            problem = problem or validate_flight_size(self.launches[i], g, self.dt)
            if problem:
                self._status("Path {}: {}".format(PATH_NAMES[i], problem))
                return False
        try:
            flights = self._build_flights(self.launches, g)
        except ValueError as err:
            self._status(str(err))
            return False
        self.g = g
        self.playback.set_flights(flights, self._visible())
        self.plot.set_flights(self.playback, self.launches_snapshot(), g)
        if not self.axes_edited:
            self._apply_auto_limits()
        self._dirty = False
        self._status("")
        return True

    # ======================================================================
    # Handlers: what each button, box and key does
    # ======================================================================

    def on_play(self, event=None) -> None:
        """Play button / space: launch new numbers if any, otherwise pause or carry on."""
        if self._dirty:
            if not self._launch():
                # The new numbers have a problem: keep the old flight, and let
                # this press still pause or carry on so you can look at it.
                self.playback.toggle_pause()
        else:
            self.playback.toggle_pause()
        self._redraw_now()

    def on_step(self, event=None) -> None:
        self.playback.step_forward()
        self._redraw_now()

    def on_jump(self, text: str) -> None:
        value = parse_number(text)
        if value is None:
            self._status("jump to t: '{}' is not a number".format(text))
        else:
            self._status("")
            self.playback.jump_to(value)
        self._redraw_now()

    def on_scrub(self, value: float) -> None:
        """Time slider dragged: go there and pause, without markers."""
        self.playback.scrub_to(value * self.playback.end_time)
        self._redraw_now()

    def on_clear(self, event=None) -> None:
        self.playback.clear_marks()
        self._redraw_now()

    def on_box_submit(self, path: int, key: str, text: str) -> None:
        """A launch box was confirmed: update that path's numbers and its other boxes."""
        box = self.boxes[(path, key)]
        if text.strip() == self._written.get(id(box)):
            return  # nothing changed
        if text.strip() == "":
            # Emptied (e.g. by clicking the equation) but nothing typed: put it back.
            self._write_path_boxes(path)
            self._set_box_color(box, BOX_COLOR if path == 0 or self.path_b_on else OFF_COLOR)
            self.fig.canvas.draw_idle()
            return
        value = parse_number(text)
        if value is None:
            self._status("'{}' is not a number".format(text))
            self._write_path_boxes(path)
            self.fig.canvas.draw_idle()
            return
        launch = self.launches[path]
        if key in ("x0", "y0"):
            setattr(launch, key, value)
        elif key == "v0":
            launch.set_polar(value, launch.angle_deg)
            self._source[path] = "polar"
        elif key == "angle_deg":
            launch.set_polar(launch.v0, value)
            self._source[path] = "polar"
        elif key == "vx":
            launch.set_components(value, launch.vy)
            self._source[path] = "components"
        elif key == "vy":
            launch.set_components(launch.vx, value)
            self._source[path] = "components"
        self._write_path_boxes(path)
        self._set_box_color(box, BOX_COLOR if path == 0 or self.path_b_on else OFF_COLOR)
        self._status("")
        self._refresh_banner()
        self._mark_dirty()

    def on_g_submit(self, text: str) -> None:
        if text.strip() == self._written.get(id(self.g_box)):
            return
        if text.strip() == "":
            self._write(self.g_box, self._written.get(id(self.g_box), _fmt(self.g)))
            self._set_box_color(self.g_box, BOX_COLOR)
            self.fig.canvas.draw_idle()
            return
        if parse_number(text) is None:
            self._status("gravity: '{}' is not a number".format(text))
            self._write(self.g_box, _fmt(self.g))
        else:
            self._status("")
            self._written[id(self.g_box)] = text.strip()
            self._mark_dirty()
        self._set_box_color(self.g_box, BOX_COLOR)
        self._refresh_banner()
        self.fig.canvas.draw_idle()

    def apply_preset(self, name: str) -> None:
        """Earth / Moon / Mars / Jupiter: fill the g box. Used on the next Play."""
        self._write(self.g_box, _fmt(GRAVITY_PRESETS[name]))
        self._status("")
        self._refresh_banner()
        self._mark_dirty()

    def on_axis_submit(self, text: str = "") -> None:
        """An axis box was confirmed: check all four and apply them right away."""
        boxes = (self.xmin_box, self.xmax_box, self.ymin_box, self.ymax_box)
        if all(box.text.strip() == self._written.get(id(box)) for box in boxes):
            return  # nothing changed
        values = [parse_number(box.text) for box in boxes]
        if any(v is None for v in values):
            problem = "axis limits must be numbers"
        else:
            problem = validate_world(self.g, *values)
        if problem:
            self._status(problem)
            for box, value in zip(boxes, self.ax.get_xlim() + self.ax.get_ylim()):
                self._write(box, _fmt(round(value, 1)))
        else:
            self._status("")
            self.plot.set_limits(*values)
            for box in boxes:
                self._written[id(box)] = box.text
            self.axes_edited = True
        self._redraw_now()

    def on_autofit(self, event=None) -> None:
        self._apply_auto_limits()
        self.axes_edited = False
        self._status("")
        self._redraw_now()

    def on_interval_submit(self, text: str) -> None:
        value = parse_number(text)
        if value is None or value <= 0:
            self._status("pause every: use a number of seconds bigger than 0")
            self._write(self.interval_box, _fmt(self.playback.pause_interval))
        else:
            self._status("")
            self._written[id(self.interval_box)] = text.strip()
            self.playback.set_auto_pause(self.playback.auto_pause, value)
        self.fig.canvas.draw_idle()

    def set_auto_pause(self, on: bool) -> None:
        """The "pause every" checkbox."""
        value = parse_number(self.interval_box.text)
        if value is None or value <= 0:
            value = self.playback.pause_interval
        self.playback.set_auto_pause(on, value)
        if self.auto_pause_check.get_status()[0] != on:
            self.auto_pause_check.eventson = False
            self.auto_pause_check.set_active(0)
            self.auto_pause_check.eventson = True
        self.fig.canvas.draw_idle()

    def set_path_b(self, on: bool) -> None:
        """The "show path B" checkbox. Shows or hides the orange ball right away."""
        self.path_b_on = on
        if self.path_b_check.get_status()[0] != on:
            self.path_b_check.eventson = False
            self.path_b_check.set_active(0)
            self.path_b_check.eventson = True
        self._grey_path_b()
        self.playback.set_visible(1, on)
        self._redraw_now()

    def set_speed(self, label: str) -> None:
        """Speed buttons. The timer keeps ticking at the same rate; each tick
        just moves the clock by (real time passed) × speed."""
        self.playback_speed = SPEEDS[label]

    def set_show(self, name: str, on: bool) -> None:
        """Show/hide toggles: name is "arrows", "numbers" or "cross"."""
        setattr(self.plot, {"arrows": "show_arrows", "numbers": "show_labels", "cross": "show_cross"}[name], on)
        self._redraw_now()

    def _on_show_clicked(self, label: str) -> None:
        arrows, numbers, cross = self.show_check.get_status()
        self.plot.show_arrows, self.plot.show_labels, self.plot.show_cross = arrows, numbers, cross
        self._redraw_now()

    def select_path(self, i: int) -> None:
        """A / B buttons on the banner: which path the equation shows."""
        self.selected_path = i
        self._refresh_banner()
        self.fig.canvas.draw_idle()

    def on_pick(self, event) -> None:
        """A number in the equation was clicked: start typing in its box."""
        key = self._piece_key.get(id(event.artist))
        if key is None:
            return
        box = self.g_box if key == "g" else self.boxes[(self.selected_path, key)]
        for other in self._all_boxes():
            if other is not box and other.capturekeystrokes:
                other.stop_typing()
        self._focus(box, clear=True)
        # The same click also reaches every box, and boxes stop typing when
        # clicked outside, so focus the box again when the mouse is released.
        self._pending_focus = box

    def _on_release(self, event) -> None:
        if self._pending_focus is not None:
            self._focus(self._pending_focus)
            self._pending_focus = None

    def _focus(self, box: TextBox, clear: bool = False) -> None:
        """Start typing in box. clear=True empties it so your typing replaces the old value."""
        if not box.capturekeystrokes:
            box.begin_typing()
        if clear:
            box.text_disp.set_text("")
        box.cursor_index = len(box.text)
        box._rendercursor()
        self._set_box_color(box, HIGHLIGHT_COLOR)

    def _all_boxes(self) -> List[TextBox]:
        return list(self.boxes.values()) + [
            self.g_box, self.xmin_box, self.xmax_box, self.ymin_box, self.ymax_box,
            self.interval_box, self.jump_box,
        ]

    def on_key(self, event) -> None:
        """Space = Play button, right arrow = Step. Ignored while typing in a box."""
        if any(box.capturekeystrokes for box in self._all_boxes()):
            return
        if event.key == " ":
            self.on_play()
        elif event.key == "right":
            self.on_step()

    # ======================================================================
    # Running
    # ======================================================================

    def tick(self, frame: int) -> None:
        """Called by the animation timer: move the clock and redraw.

        The simulated clock moves by (real seconds since the last tick) × speed,
        so 1× really is real time even if the computer draws slowly.
        """
        now = self.clock()
        if self._last_tick is not None and not self.playback.paused:
            real_seconds = min(now - self._last_tick, 0.1)  # don't leap after a hiccup
            self.playback.advance(real_seconds * self.playback_speed)
        self._last_tick = now
        self._refresh()

    def _frame_ms(self) -> float:
        """How often the timer redraws the window, in milliseconds."""
        return self.playback.frame_dt * 1000

    def run(self) -> None:
        """Open the window and start the animation timer."""
        disable_matplotlib_shortcuts()
        self._animation = FuncAnimation(self.fig, self.tick, interval=self._frame_ms(), cache_frame_data=False)
        plt.show()
