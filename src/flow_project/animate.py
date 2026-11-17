"""Drawing code: draws one or two flights onto a matplotlib plot.

Nothing in here does physics. The physics lives in `projectile.py`; this file
only draws what the Playback says is happening right now. It does not open a
window either: `launch_window.py` puts this plot inside the window.
"""

import math
from typing import List, Optional, Tuple

import numpy as np

from src.flow_project.launch import Launch
from src.flow_project.player import PathState, Playback
from src.flow_project.projectile import Flight, exact_position

# ---------------------------------------------------------------------------
# Settings for how things look
# ---------------------------------------------------------------------------
PATH_COLORS = ["#0b6e8e", "#c2491d"]  # Path A blue, Path B orange
SPEED_COLOR = "#4a3e8a"  # the "v ..." label
MARK_COLOR = "#8a8f98"  # ghost markers left at every pause
CROSS_COLOR = "black"  # where the equation says the ball should be
ARROW_FRACTION = 0.15  # fastest speed gets an arrow this fraction of the plot width
LABEL_FLIP = 0.75  # labels jump to the ball's left past this fraction of the width
PATH_NAMES = ["A", "B"]
EDGE_ROOM = 0.02  # auto-fit leaves this fraction of room past the flight's edges


# --- helper functions --------------------------------------------------------


def auto_limits(flights: List[Flight]) -> Tuple[float, float, float, float]:
    """(xmin, xmax, ymin, ymax) that fit every flight, never narrower than 1 m."""
    lo = min(float(f.x.min()) for f in flights)
    hi = max(float(f.x.max()) for f in flights)
    if hi - lo < 1e-9:
        # Every ball stays at one x (straight up or down): centre it.
        xmin, xmax = lo - 0.5, lo + 0.5
    else:
        xmin = 1.1 * lo if lo < 0 else 0.0
        xmax = 1.1 * hi if hi > 0 else 0.0
        if xmax - xmin < 1.0:
            xmax = xmin + 1.0
        # Leave a sliver of room so a ball sitting on an edge isn't cut in half
        width = xmax - xmin
        xmin = min(xmin, lo - EDGE_ROOM * width)
        xmax = max(xmax, hi + EDGE_ROOM * width)
    ymax = max(1.25 * max(float(f.y.max()) for f in flights), 1.0)
    return xmin, xmax, -EDGE_ROOM * ymax, ymax


def label_side(x: float, xmin: float, xmax: float) -> str:
    """Which side of the ball its numbers go, so they stay inside the plot."""
    return "left" if x > xmin + LABEL_FLIP * (xmax - xmin) else "right"


def format_readout_table(
    states: List[Optional[PathState]],
    flights: List[Optional[Flight]],
    gaps: List[Optional[float]],
) -> str:
    """The readout table: one column per path, "—" where a path is off."""

    def cell(value: Optional[float], digits: int) -> str:
        return "—" if value is None else "{:.{d}f}".format(value, d=digits)

    def row(name: str, values: List[Optional[float]], digits: int) -> str:
        return "{:<8}".format(name) + "".join("{:>9}".format(cell(v, digits)) for v in values)

    pick = lambda items, fn: [None if it is None else fn(it) for it in items]  # noqa: E731
    lines = ["{:<8}".format("") + "".join("{:>9}".format(n) for n in PATH_NAMES[: len(states)])]
    lines.append(row("x m", pick(states, lambda s: s.x), 1))
    lines.append(row("y m", pick(states, lambda s: s.y), 1))
    lines.append(row("vx m/s", pick(states, lambda s: s.vx), 1))
    lines.append(row("vy m/s", pick(states, lambda s: s.vy), 1))
    lines.append(row("v m/s", pick(states, lambda s: s.speed), 1))
    lines.append(row("range m", pick(flights, lambda f: f.range), 1))
    lines.append(row("max h m", pick(flights, lambda f: f.max_height), 1))
    lines.append(row("flight s", pick(flights, lambda f: f.flight_time), 2))
    lines.append(row("sim−eq m", gaps, 3))
    return "\n".join(lines)


# --- the plot ----------------------------------------------------------------


class FlightPlot:
    """Draws every path in a Playback onto one matplotlib Axes."""

    def __init__(self, ax, playback: Playback, launches: List[Launch], g: float) -> None:
        self.ax = ax
        self.show_arrows = True
        self.show_labels = True
        self.show_cross = True

        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.grid(True, alpha=0.3)
        ax.axhline(0, color="black", linewidth=1.5)  # the ground

        self.marks_scatter = ax.scatter(
            [], [], s=80, facecolors="none", edgecolors=MARK_COLOR, linewidths=1.5, zorder=3
        )
        self.mark_labels: list = []
        self.clock_text = ax.text(
            0.98, 0.96, "", transform=ax.transAxes, ha="right", va="top",
            fontsize=13, fontweight="bold", family="monospace",
        )
        self._path_artists: list = []
        self.set_flights(playback, launches, g)
        self.set_limits(*auto_limits(playback.flights))

    # --- setup --------------------------------------------------------------

    def set_flights(self, playback: Playback, launches: List[Launch], g: float) -> None:
        """Use new flights (after Play). `launches` must be the numbers they were built from."""
        self.playback = playback
        self.launches = list(launches)
        self.g = g
        if len(self._path_artists) != len(playback.flights):
            for artist in self._path_artists:
                artist.remove()
            self._make_path_artists(len(playback.flights))

    def _make_path_artists(self, n: int) -> None:
        ax = self.ax
        self.balls, self.trails, self.crosses = [], [], []
        self.vx_arrows, self.vy_arrows, self.label_texts = [], [], []
        self._path_artists = []
        text_style = dict(fontsize=10, fontweight="bold", family="monospace", zorder=5)
        for i in range(n):
            color = PATH_COLORS[i % len(PATH_COLORS)]
            (trail,) = ax.plot([], [], linestyle=":", color=color, linewidth=1.8)
            (ball,) = ax.plot([], [], marker="o", markersize=11, color=color, zorder=4)
            (cross,) = ax.plot([], [], marker="x", markersize=9, color=CROSS_COLOR, mew=1.5, zorder=6)
            props = dict(arrowstyle="->", linewidth=2.2, color=color, shrinkA=0, shrinkB=0)
            vx_arrow = ax.annotate("", xy=(0, 0), xytext=(0, 0), arrowprops=props)
            vy_arrow = ax.annotate("", xy=(0, 0), xytext=(0, 0), arrowprops=dict(props))
            line1 = ax.text(0, 0, "", color=color, **text_style)
            line2 = ax.text(0, 0, "", color=SPEED_COLOR, **text_style)
            self.trails.append(trail)
            self.balls.append(ball)
            self.crosses.append(cross)
            self.vx_arrows.append(vx_arrow)
            self.vy_arrows.append(vy_arrow)
            self.label_texts.append((line1, line2))
            self._path_artists += [trail, ball, cross, vx_arrow, vy_arrow, line1, line2]

    def set_limits(self, xmin: float, xmax: float, ymin: float, ymax: float) -> None:
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)

    # --- numbers ------------------------------------------------------------

    def exact_point(self, i: int) -> Tuple[float, float]:
        """Where the equation r(t) says ball i should be at its current time."""
        s = self.playback.state(i)
        launch = self.launches[i]
        return exact_position(s.t, launch.v0, launch.angle_deg, self.g, launch.y0, launch.x0)

    def gap(self, i: int) -> float:
        """Distance in metres between the simulated ball and the equation's point."""
        s = self.playback.state(i)
        ex, ey = self.exact_point(i)
        return math.hypot(s.x - ex, s.y - ey)

    def _arrow_scales(self) -> Tuple[float, float]:
        """Metres of arrow per m/s, one per axis, so 1 m/s looks the same both ways."""
        box = self.ax.get_window_extent()
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        pb = self.playback
        speeds = [float(f.speed.max()) for f, on in zip(pb.flights, pb.visible) if on]
        fastest = max(speeds + [1e-9])
        px_per_mps = ARROW_FRACTION * box.width / fastest  # pixels per m/s
        return px_per_mps * (xmax - xmin) / box.width, px_per_mps * (ymax - ymin) / box.height

    # --- drawing ------------------------------------------------------------

    def draw(self) -> None:
        """Redraw everything from the Playback's current moment."""
        pb = self.playback
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        width, height = xmax - xmin, ymax - ymin
        scale_x, scale_y = self._arrow_scales()
        # With two balls showing, the higher one's numbers go above it and the
        # lower one's go below it, so the two sets never sit on top of each other.
        shown = [i for i, on in enumerate(pb.visible) if on]
        highest = max(shown, key=lambda k: pb.state(k).y) if len(shown) > 1 else None

        for i, flight in enumerate(pb.flights):
            on = pb.visible[i]
            s = pb.state(i)
            j = len(flight.t) - 1 if s.landed else flight.index_at_time(pb.t)

            self.trails[i].set_data(flight.x[: j + 1], flight.y[: j + 1])
            self.balls[i].set_data([s.x], [s.y])
            ex, ey = self.exact_point(i)
            self.crosses[i].set_data([ex], [ey])

            # (xyann is the arrow's tail, xy is its head)
            self.vx_arrows[i].xyann = (s.x, s.y)
            self.vx_arrows[i].xy = (s.x + s.vx * scale_x, s.y)
            self.vy_arrows[i].xyann = (s.x, s.y)
            self.vy_arrows[i].xy = (s.x, s.y + s.vy * scale_y)

            # Numbers ride next to the ball, past the tip of the sideways arrow
            side = label_side(s.x, xmin, xmax)
            offset = 0.03 * width + abs(s.vx) * scale_x
            label_x = s.x + offset if side == "right" else s.x - offset
            low, high = ymin + 0.03 * height, ymax - 0.03 * height  # stay inside the plot
            gap = 0.06 * height  # space between the two lines of numbers
            if highest is None:
                line2_y = s.y - 0.035 * height  # one ball: numbers beside it
            elif i == highest:
                line2_y = s.y + 0.03 * height  # numbers above the ball
            else:
                line2_y = s.y - 0.04 * height - gap  # numbers below the ball
            line2_y = min(max(line2_y, low), high - gap)
            line1, line2 = self.label_texts[i]
            line1.set_text("vx {:.1f}  vy {:+.1f}".format(s.vx, s.vy))
            line2.set_text("v {:.1f}".format(s.speed))
            for text, y in ((line1, line2_y + gap), (line2, line2_y)):
                text.set_position((label_x, y))
                text.set_ha("left" if side == "right" else "right")

            for artist in (self.trails[i], self.balls[i]):
                artist.set_visible(on)
            self.crosses[i].set_visible(on and self.show_cross)
            self.vx_arrows[i].set_visible(on and self.show_arrows)
            self.vy_arrows[i].set_visible(on and self.show_arrows)
            line1.set_visible(on and self.show_labels)
            line2.set_visible(on and self.show_labels)

        clock = "t = {:.2f} s".format(pb.t)
        if pb.paused:
            clock += " (paused)"
        self.clock_text.set_text(clock)
        self._draw_marks(height, ymin)

    def _draw_marks(self, height: float, ymin: float) -> None:
        marks = self.playback.marks
        self.marks_scatter.set_offsets(np.array([(x, y) for _, x, y, _ in marks]).reshape(-1, 2))
        if len(self.mark_labels) > len(marks):  # markers were cleared
            for text in self.mark_labels:
                text.remove()
            self.mark_labels = []
        for _, x, y, t in marks[len(self.mark_labels):]:
            self.mark_labels.append(
                self.ax.text(
                    x, max(y - 0.035 * height, ymin + 0.005 * height), "{:.1f}s".format(t),
                    ha="center", va="top", fontsize=8, color=MARK_COLOR,
                )
            )
