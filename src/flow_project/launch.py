"""The starting numbers for one path, as typed into the boxes on screen.

A launch velocity is one arrow. You can describe it two ways:
  - by its length and direction: v0 (speed) and θ (angle above the ground), or
  - by its sideways and upward parts: vx and vy.
Both describe the same arrow, so changing one pair changes the other pair.
This file keeps the two pairs in step, and checks typed numbers make sense.
"""

import math
from dataclasses import dataclass
from typing import Dict, Optional

from src.flow_project.projectile import exact_flight_time

# Longest flight we'll simulate, in time slices (about 80 MB of memory)
MAX_SAMPLES = 2_000_000


@dataclass
class Launch:
    """Where and how one ball is thrown."""

    x0: float = 0.0  # m, starting sideways position
    y0: float = 0.0  # m, starting height
    v0: float = 20.0  # m/s, launch speed
    angle_deg: float = 45.0  # degrees above the ground

    @property
    def vx(self) -> float:
        """Sideways part of the launch velocity, m/s."""
        return self.v0 * math.cos(math.radians(self.angle_deg))  # PHYSICS: vx = v0 cos θ

    @property
    def vy(self) -> float:
        """Upward part of the launch velocity, m/s."""
        return self.v0 * math.sin(math.radians(self.angle_deg))  # PHYSICS: vy = v0 sin θ

    def set_components(self, vx: float, vy: float) -> None:
        """Typed vx and vy: work out the matching speed and angle."""
        self.v0 = math.hypot(vx, vy)  # PHYSICS: v0 = √(vx² + vy²)
        self.angle_deg = math.degrees(math.atan2(vy, vx))  # PHYSICS: θ = angle of (vx, vy)

    def set_polar(self, v0: float, angle_deg: float) -> None:
        """Typed speed and angle."""
        self.v0 = v0
        self.angle_deg = angle_deg

    def as_dict(self) -> Dict[str, float]:
        """All six numbers, keyed by the name of their box."""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "v0": self.v0,
            "angle_deg": self.angle_deg,
            "vx": self.vx,
            "vy": self.vy,
        }


def parse_number(text: str) -> Optional[float]:
    """Turn what was typed in a box into a number, or None if it isn't one."""
    try:
        value = float(text.strip())
    except ValueError:
        return None
    # "nan", "inf" and numbers too big to store are not useful numbers here
    return value if math.isfinite(value) else None


def validate_launch(launch: Launch) -> Optional[str]:
    """A plain-English problem with this launch, or None if it's fine."""
    if launch.y0 < 0:
        return "start height can't be below the ground"
    if launch.v0 < 0:
        return "speed can't be negative"
    return None


def validate_world(g: float, xmin: float, xmax: float, ymin: float, ymax: float) -> Optional[str]:
    """A plain-English problem with gravity or the axes, or None if fine."""
    if g <= 0:
        return "gravity must be a positive number"
    if xmax <= xmin:
        return "x max must be bigger than x min"
    if ymax <= ymin:
        return "y max must be bigger than y min"
    return None


def validate_flight_size(launch: Launch, g: float, dt: float) -> Optional[str]:
    """A message if this flight would take too many time slices to simulate."""
    flight_time = exact_flight_time(abs(launch.v0), launch.angle_deg, g, max(launch.y0, 0.0))
    if flight_time / dt > MAX_SAMPLES:
        return (
            "that flight would last {:.0f} s, too long to simulate. "
            "Try a smaller speed or bigger gravity".format(flight_time)
        )
    return None
