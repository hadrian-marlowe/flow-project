"""Physics engine for a ball flying under gravity with no air.

This is a *time-stepping* simulation. Instead of plugging numbers into the
parabola formulas, we move the ball forward in tiny slices of time. In each
slice gravity nudges the velocity, then the velocity nudges the position.
Later projects add more forces (like air resistance) to the same loop.

Every line that does physics is marked with a `# PHYSICS:` comment.

The exact formulas (`exact_*` functions) are the textbook answers. They are
used by the tests to prove the simulation is right, and for the "max height"
and "range" readouts on screen.
"""

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class Flight:
    """The stored result of one simulated flight.

    Every array has the same length; index i is one moment in time.
    """

    t: np.ndarray  # time, s
    x: np.ndarray  # sideways position, m
    y: np.ndarray  # height, m
    vx: np.ndarray  # sideways velocity, m/s
    vy: np.ndarray  # up/down velocity, m/s (negative = falling)

    @property
    def speed(self) -> np.ndarray:
        """Total speed at every moment (length of the velocity arrow)."""
        return np.hypot(self.vx, self.vy)  # PHYSICS: speed = sqrt(vx² + vy²)

    @property
    def flight_time(self) -> float:
        """Time when the ball lands, s."""
        return float(self.t[-1])

    @property
    def max_height(self) -> float:
        """Highest point reached, m."""
        return float(self.y.max())

    @property
    def range(self) -> float:
        """How far sideways the ball travelled before landing, m."""
        return float(self.x[-1])

    def index_at_time(self, t: float) -> int:
        """Index of the stored sample closest to time t (clamped to the ends)."""
        i = int(np.argmin(np.abs(self.t - t)))
        return max(0, min(i, len(self.t) - 1))


def step(
    x: float, y: float, vx: float, vy: float, dt: float, g: float
) -> Tuple[float, float, float, float]:
    """Move the ball forward by one tiny slice of time `dt`.

    Gravity only pulls down, so vx never changes. We update the velocity first
    and then use the *new* velocity to move the position (this is called
    "semi-implicit Euler" and is a little more accurate than the other order).
    """
    vy_new = vy - g * dt  # PHYSICS: gravity slows the upward velocity by g each second
    x_new = x + vx * dt  # PHYSICS: sideways position moves at a constant vx
    y_new = y + vy_new * dt  # PHYSICS: height moves by the (new) vertical velocity
    return x_new, y_new, vx, vy_new


def _check_gravity(g: float) -> None:
    if g <= 0:
        raise ValueError("gravity must be a positive number (like 9.8)")


def _launch_velocity(speed: float, angle_deg: float) -> Tuple[float, float]:
    """Split a launch speed and angle into sideways and upward parts."""
    angle = math.radians(angle_deg)
    vx = speed * math.cos(angle)  # PHYSICS: sideways part of the launch velocity
    vy = speed * math.sin(angle)  # PHYSICS: upward part of the launch velocity
    return vx, vy


def simulate(
    speed: float,
    angle_deg: float,
    g: float = 9.8,
    start_height: float = 0.0,
    dt: float = 0.001,
) -> Flight:
    """Run the whole flight in tiny time slices and return the stored samples.

    The loop runs until the ball comes back down to the ground (y = 0). The
    last sample is clipped so it sits exactly on the ground.
    """
    _check_gravity(g)
    vx, vy = _launch_velocity(speed, angle_deg)
    t, x, y = 0.0, 0.0, start_height

    ts, xs, ys, vxs, vys = [t], [x], [y], [vx], [vy]

    # Already on the ground and not going up: there is no flight at all.
    if y <= 0 and vy <= 0:
        return Flight(np.array(ts), np.array(xs), np.array(ys), np.array(vxs), np.array(vys))

    while True:
        x_new, y_new, vx_new, vy_new = step(x, y, vx, vy, dt, g)  # PHYSICS: one time slice
        t_new = t + dt
        if y_new < 0:
            # The ball crossed below the ground during this slice. Find the
            # fraction of the slice where it hit y = 0 and clip to that point.
            fraction = y / (y - y_new)  # 0 = start of slice, 1 = end of slice
            t_hit = t + fraction * dt
            x_hit = x + fraction * (x_new - x)
            vy_hit = vy + fraction * (vy_new - vy)
            ts.append(t_hit)
            xs.append(x_hit)
            ys.append(0.0)
            vxs.append(vx_new)
            vys.append(vy_hit)
            break
        t, x, y, vx, vy = t_new, x_new, y_new, vx_new, vy_new
        ts.append(t)
        xs.append(x)
        ys.append(y)
        vxs.append(vx)
        vys.append(vy)

    return Flight(np.array(ts), np.array(xs), np.array(ys), np.array(vxs), np.array(vys))


def exact_position(
    t: float, speed: float, angle_deg: float, g: float = 9.8, start_height: float = 0.0
) -> Tuple[float, float]:
    """Textbook position at time t (no air)."""
    vx, vy = _launch_velocity(speed, angle_deg)
    x = vx * t  # PHYSICS: x = vx · t
    y = start_height + vy * t - 0.5 * g * t * t  # PHYSICS: y = h + vy·t − ½·g·t²
    return x, y


def exact_velocity(
    t: float, speed: float, angle_deg: float, g: float = 9.8
) -> Tuple[float, float]:
    """Textbook velocity at time t (no air)."""
    vx, vy = _launch_velocity(speed, angle_deg)
    return vx, vy - g * t  # PHYSICS: vx stays the same; vy = vy0 − g·t


def exact_flight_time(
    speed: float, angle_deg: float, g: float = 9.8, start_height: float = 0.0
) -> float:
    """Textbook time until the ball lands (solves y = 0 for t)."""
    _check_gravity(g)
    _, vy = _launch_velocity(speed, angle_deg)
    # PHYSICS: 0 = h + vy·t − ½·g·t²  →  t = (vy + sqrt(vy² + 2·g·h)) / g
    return (vy + math.sqrt(vy * vy + 2 * g * start_height)) / g
