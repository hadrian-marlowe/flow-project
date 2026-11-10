"""Drawing code: turns a stored Flight and a Player into a matplotlib animation.

Nothing in here does physics. The physics lives in `projectile.py`; this file
only draws what the Player says is on screen right now.
"""

from typing import Optional, Tuple

import numpy as np

from src.flow_project.projectile import Flight

# --- helper functions (no matplotlib needed) ---------------------------------


def parse_jump_time(text: str, flight_time: float) -> Optional[float]:
    """Turn what was typed in the jump box into a time, or None to ignore it.

    "1.25" → 1.25; blank, words, "1,25" or negatives → None;
    anything past the landing time is clamped to the landing time.
    """
    try:
        value = float(text.strip())
    except ValueError:
        return None
    if value < 0:
        return None
    return min(value, flight_time)


def axis_limits(flight: Flight) -> Tuple[float, float]:
    """(xmax, ymax) for the plot: a little bigger than the flight, never zero."""
    xmax = max(flight.range * 1.1, 1.0)
    ymax = max(flight.max_height * 1.25, 1.0)
    return xmax, ymax


def label_side(x: float, xmax: float) -> str:
    """Which side of the ball the labels go on so they stay inside the plot."""
    return "left" if x > 0.75 * xmax else "right"


def format_readout(
    t: float,
    x: float,
    y: float,
    vx: float,
    vy: float,
    speed: float,
    max_height: float,
    rng: float,
) -> str:
    """The side-panel text, one value per line."""
    return "\n".join(
        [
            "t = {:.2f} s".format(t),
            "x = {:.1f} m".format(x),
            "y = {:.1f} m".format(y),
            "vx = {:.1f} m/s".format(vx),
            "vy = {:.1f} m/s".format(vy),
            "speed = {:.1f} m/s".format(speed),
            "max height = {:.1f} m".format(max_height),
            "range = {:.1f} m".format(rng),
        ]
    )


# --- the animation window ----------------------------------------------------

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation  # noqa: E402
from matplotlib.widgets import TextBox  # noqa: E402

from src.flow_project.player import Player  # noqa: E402

# Colours (same as the mockup)
BALL_COLOR = "#0b6e8e"  # ball and the sideways (vx) arrow
VY_COLOR = "#c2491d"  # the up/down (vy) arrow
SPEED_COLOR = "#4a3e8a"  # total speed label
MARK_COLOR = "#8a8f98"  # ghost markers left at every pause

# How long the arrows are: the fastest speed in the flight gets an arrow this
# fraction of the plot width. Slower speeds get proportionally shorter arrows.
ARROW_FRACTION = 0.15


class FlightAnimation:
    """Draws a Flight as it plays back through a Player.

    Keys while the window is open:
      space        pause / resume (leaves a ghost marker)
      right arrow  step forward by one pause interval
      jump box     type a time in seconds and press Enter
    """

    def __init__(
        self,
        flight: Flight,
        player: Player,
        playback_speed: float = 0.5,
        title: str = "Ball with no air",
        arrow_fraction: float = ARROW_FRACTION,
    ) -> None:
        self.flight = flight
        self.player = player
        self.playback_speed = playback_speed
        self._animation = None  # FuncAnimation, kept alive while the window is open
        self._jumping = False  # guards against the jump box firing twice

        self.fig, self.ax = plt.subplots(figsize=(10, 6.5))
        self.fig.subplots_adjust(bottom=0.2, right=0.78)
        if self.fig.canvas.manager is not None:
            self.fig.canvas.manager.set_window_title(title)

        xmax, ymax = axis_limits(flight)
        self.xmax = xmax
        if flight.range < 1e-6:
            # Straight up or straight down: centre the ball instead of pinning
            # it to the left edge of the plot.
            self.ax.set_xlim(-xmax / 2, xmax / 2)
        else:
            self.ax.set_xlim(0, xmax)
        self.ax.set_ylim(0, ymax)

        # Arrow length in metres per m/s, one scale per axis. The x and y axes
        # are stretched differently on screen, so we correct for the shape of
        # the plot area to make 1 m/s the same number of pixels in both
        # directions. Then equal vx and vy really look equal.
        box = self.ax.get_window_extent()
        px_per_m_x = box.width / (self.ax.get_xlim()[1] - self.ax.get_xlim()[0])
        px_per_m_y = box.height / ymax
        fastest = max(float(flight.speed.max()), 1e-9)
        px_per_mps = arrow_fraction * box.width / fastest  # pixels per m/s
        self.arrow_scale_x = px_per_mps / px_per_m_x
        self.arrow_scale_y = px_per_mps / px_per_m_y
        self.ax.set_xlabel("x (m)")
        self.ax.set_ylabel("y (m)")
        self.ax.set_title(title)
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(0, color="black", linewidth=1.5)  # the ground

        # Create every artist once; draw_frame only moves them around.
        (self.trail,) = self.ax.plot([], [], linestyle=":", color=BALL_COLOR, linewidth=1.5)
        (self.ball,) = self.ax.plot([], [], marker="o", markersize=12, color=BALL_COLOR)
        self.marks_scatter = self.ax.scatter(
            [], [], s=90, facecolors="none", edgecolors=MARK_COLOR, linewidths=1.5
        )
        self.mark_labels = []  # one small text per ghost marker

        arrow_style = dict(arrowstyle="->", linewidth=2.5, shrinkA=0, shrinkB=0)
        self.vx_arrow = self.ax.annotate(
            "", xy=(0, 0), xytext=(0, 0), arrowprops=dict(color=BALL_COLOR, **arrow_style)
        )
        self.vy_arrow = self.ax.annotate(
            "", xy=(0, 0), xytext=(0, 0), arrowprops=dict(color=VY_COLOR, **arrow_style)
        )

        text_style = dict(fontsize=11, fontweight="bold", family="monospace")
        self.vx_text = self.ax.text(0, 0, "", color=BALL_COLOR, **text_style)
        self.vy_text = self.ax.text(0, 0, "", color=VY_COLOR, **text_style)
        self.speed_text = self.ax.text(0, 0, "", color=SPEED_COLOR, **text_style)

        self.clock_text = self.ax.text(
            0.98, 0.95, "", transform=self.ax.transAxes, ha="right", va="top",
            fontsize=14, fontweight="bold", family="monospace",
        )
        self.readout_text = self.fig.text(
            0.80, 0.85, "", va="top", fontsize=11, family="monospace",
        )
        self.fig.text(
            0.80, 0.42, "space: pause/play\nright arrow: step\nbox: jump to a time",
            va="top", fontsize=9, color=MARK_COLOR,
        )

        self.textbox = TextBox(self.fig.add_axes([0.25, 0.05, 0.25, 0.06]), "Jump to t (s)  ")
        self.textbox.on_submit(self.on_jump)
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)

    # --- drawing --------------------------------------------------------

    def draw_frame(self, frame_number: int) -> None:
        """Called once per animation frame: move the player, then redraw."""
        self.player.advance()
        p = self.player
        i = p.index

        self.trail.set_data(self.flight.x[: i + 1], self.flight.y[: i + 1])
        self.ball.set_data([p.x], [p.y])

        # Velocity arrows, drawn in metres so they scale with the plot
        # (xyann is the arrow's tail, xy is its head)
        self.vx_arrow.xyann = (p.x, p.y)
        self.vx_arrow.xy = (p.x + p.vx * self.arrow_scale_x, p.y)
        self.vy_arrow.xyann = (p.x, p.y)
        self.vy_arrow.xy = (p.x, p.y + p.vy * self.arrow_scale_y)

        # Labels ride next to the ball and flip to its left near the right edge
        side = label_side(p.x, self.xmax)
        # Push the labels past the tip of the sideways arrow so they never overlap it
        offset = 0.03 * self.xmax + abs(p.vx) * self.arrow_scale_x
        label_x = p.x + offset if side == "right" else p.x - offset
        ha = "left" if side == "right" else "right"
        line = 0.06 * self.ax.get_ylim()[1]
        for text, dy in ((self.vx_text, line), (self.vy_text, 0.0), (self.speed_text, -line)):
            text.set_position((label_x, p.y + dy))
            text.set_ha(ha)
        self.vx_text.set_text("vx {:.1f}".format(p.vx))
        self.vy_text.set_text("vy {:+.1f}".format(p.vy))
        self.speed_text.set_text("v {:.1f}".format(p.speed))

        clock = "t = {:.2f} s".format(p.t)
        if p.paused:
            clock += " (paused)"
        self.clock_text.set_text(clock)
        self.readout_text.set_text(
            format_readout(
                p.t, p.x, p.y, p.vx, p.vy, p.speed, self.flight.max_height, self.flight.range
            )
        )
        self._draw_marks()

    def _draw_marks(self) -> None:
        marks = self.player.marks
        self.marks_scatter.set_offsets(np.array([(x, y) for x, y, _ in marks]).reshape(-1, 2))
        # Add a time label for any new marker
        for x, y, t in marks[len(self.mark_labels):]:
            self.mark_labels.append(
                self.ax.text(
                    x, y - 0.05 * self.ax.get_ylim()[1], "{:.1f}s".format(t),
                    ha="center", va="top", fontsize=8, color=MARK_COLOR,
                )
            )

    # --- controls -------------------------------------------------------

    def on_key(self, event) -> None:
        """Keyboard handler. Ignores keys typed into the jump box."""
        if getattr(event, "inaxes", None) is self.textbox.ax or self.textbox.capturekeystrokes:
            return
        if event.key == " ":
            self.player.toggle_pause()
        elif event.key == "right":
            self.player.step_forward()
        if self.player.paused:
            # Redraw now so the pause shows even though advance() has stopped
            self.draw_frame(0)
            self.fig.canvas.draw_idle()

    def on_jump(self, text: str) -> None:
        """Jump-box handler: go to the typed time, if it makes sense."""
        if self._jumping:
            return  # stop_typing() below re-fires submit; ignore that echo
        self._jumping = True
        try:
            # Pressing Enter does not take the cursor out of the box by itself,
            # so the next space would be typed into the box instead of pausing.
            self.textbox.stop_typing()
            target = parse_jump_time(text, self.flight.flight_time)
            if target is None:
                return
            self.player.jump_to(target)
            self.draw_frame(0)
            self.fig.canvas.draw_idle()
        finally:
            self._jumping = False

    # --- run ------------------------------------------------------------

    def run(self) -> None:
        """Open the window and play."""
        interval_ms = self.player.frame_dt / self.playback_speed * 1000
        self._animation = FuncAnimation(
            self.fig, self.draw_frame, interval=interval_ms, cache_frame_data=False
        )
        plt.show()
