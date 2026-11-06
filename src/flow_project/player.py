"""Playback state for a stored flight: where we are, paused or not, ghost marks.

This file has no drawing code in it. It only answers questions like "which
sample should be on screen now?" and "did a pause just happen?". The drawing
code in `animate.py` asks a Player these questions every frame.
"""

from typing import List, Optional, Tuple

from src.flow_project.projectile import Flight

# Tiny tolerance so 0.5 counts as "already at 0.5" and not "just before 0.5"
_EPS = 1e-9


def next_pause_time(current_t: float, interval: float) -> float:
    """The next multiple of `interval` that is strictly after `current_t`.

    Examples: (0.0, 0.5) → 0.5; (0.49, 0.5) → 0.5; (0.5, 0.5) → 1.0.
    """
    if interval <= 0:
        raise ValueError("pause interval must be a positive number of seconds")
    k = int((current_t + _EPS) // interval) + 1
    return k * interval


class Player:
    """Keeps track of playback for one Flight."""

    def __init__(
        self,
        flight: Flight,
        frame_dt: float = 0.02,
        pause_interval: float = 0.5,
        auto_pause: bool = True,
    ) -> None:
        self.flight = flight
        self.frame_dt = frame_dt
        self.pause_interval = pause_interval
        self.auto_pause = auto_pause

        self.index = 0  # which stored sample is on screen
        self.paused = False
        self.marks: List[Tuple[float, float, float]] = []  # (x, y, t) ghost markers
        self._next_stop: Optional[float] = None
        self._update_next_stop()

    # --- current values -------------------------------------------------

    @property
    def t(self) -> float:
        return float(self.flight.t[self.index])

    @property
    def x(self) -> float:
        return float(self.flight.x[self.index])

    @property
    def y(self) -> float:
        return float(self.flight.y[self.index])

    @property
    def vx(self) -> float:
        return float(self.flight.vx[self.index])

    @property
    def vy(self) -> float:
        return float(self.flight.vy[self.index])

    @property
    def speed(self) -> float:
        return float(self.flight.speed[self.index])

    @property
    def finished(self) -> bool:
        return self.index >= len(self.flight.t) - 1

    # --- controls -------------------------------------------------------

    def advance(self) -> None:
        """Move forward by one animation frame (does nothing if paused or done)."""
        if self.paused or self.finished:
            return
        target = self.t + self.frame_dt
        stop_here = self._next_stop is not None and target >= self._next_stop - _EPS
        if stop_here:
            target = self._next_stop
        self._go_to(target)
        if stop_here or self.finished:
            self._pause_here()

    def toggle_pause(self) -> None:
        """Space bar: pause (leaving a ghost marker) or resume."""
        if self.paused:
            self.paused = False
        else:
            self._pause_here()

    def step_forward(self) -> None:
        """Right arrow: jump ahead by one pause interval and pause there."""
        self._go_to(self.t + self.pause_interval)
        self._pause_here()

    def jump_to(self, t: float) -> None:
        """Jump box: go to the stored sample nearest time t and pause there."""
        self._go_to(t)
        self._pause_here()

    # --- helpers --------------------------------------------------------

    def _go_to(self, t: float) -> None:
        t = max(0.0, min(t, self.flight.flight_time))
        self.index = self.flight.index_at_time(t)

    def _pause_here(self) -> None:
        self.paused = True
        mark = (self.flight.x[self.index], self.flight.y[self.index], self.flight.t[self.index])
        if not self.marks or self.marks[-1][2] != mark[2]:
            self.marks.append(mark)
        self._update_next_stop()

    def _update_next_stop(self) -> None:
        if self.auto_pause:
            self._next_stop = next_pause_time(self.t, self.pause_interval)
        else:
            self._next_stop = None
