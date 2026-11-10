"""Drawing code: turns a stored Flight and a Player into a matplotlib animation.

Nothing in here does physics. The physics lives in `projectile.py`; this file
only draws what the Player says is on screen right now.
"""

from typing import Optional, Tuple

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
