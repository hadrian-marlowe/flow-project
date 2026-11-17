"""Playback: one shared clock for one or two stored flights.

There is no drawing code in here. It only answers questions like "what time is
it?", "are we paused?" and "where is each ball right now?". The drawing code
in `animate.py` asks these questions every frame.

The clock `t` is a smooth number of seconds. Each ball shows the stored
physics sample closest to that time. When a ball has landed it stays on the
ground while the clock keeps running for the other ball.
"""

from typing import List, NamedTuple, Optional, Tuple

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


class PathState(NamedTuple):
    """Everything about one ball at the current moment."""

    x: float
    y: float
    vx: float
    vy: float
    speed: float
    t: float  # the time of the stored sample being shown
    landed: bool


class Playback:
    """Keeps track of time, pausing and ghost markers for 1 or 2 flights."""

    def __init__(
        self,
        flights: List[Flight],
        frame_dt: float = 0.02,
        pause_interval: float = 0.5,
        auto_pause: bool = False,
        visible: Optional[List[bool]] = None,
    ) -> None:
        self.frame_dt = frame_dt
        self.pause_interval = pause_interval
        self.auto_pause = auto_pause
        # (path index, x, y, t) for every ghost marker, in the order added
        self.marks: List[Tuple[int, float, float, float]] = []
        self.set_flights(flights, visible)

    # --- what is happening right now ---------------------------------------

    @property
    def end_time(self) -> float:
        """When the last visible ball lands (0 if no ball is visible)."""
        times = [f.flight_time for f, on in zip(self.flights, self.visible) if on]
        return max(times) if times else 0.0

    @property
    def finished(self) -> bool:
        return self.t >= self.end_time - _EPS

    def state(self, i: int) -> PathState:
        """Where ball i is at the current time (on the ground once it has landed)."""
        flight = self.flights[i]
        landed = self.t >= flight.flight_time - _EPS
        j = len(flight.t) - 1 if landed else flight.index_at_time(self.t)
        return PathState(
            x=float(flight.x[j]),
            y=float(flight.y[j]),
            vx=float(flight.vx[j]),
            vy=float(flight.vy[j]),
            speed=float(flight.speed[j]),
            t=float(flight.t[j]),
            landed=landed,
        )

    # --- controls -----------------------------------------------------------

    def advance(self, dt: Optional[float] = None) -> None:
        """Move the clock forward by dt seconds (one frame if not given).

        Does nothing while paused or after the last ball lands.
        """
        if self.paused or self.finished:
            return
        target = self.t + (self.frame_dt if dt is None else dt)
        stop_here = self._next_stop is not None and target >= self._next_stop - _EPS
        if stop_here:
            target = self._next_stop
        self.t = min(target, self.end_time)
        if stop_here and not self.finished:
            # Count the next stop from the one we aimed at, so we never re-stop here.
            self._pause_here(next_stop=self._next_stop + self.pause_interval)
        elif self.finished:
            self._pause_here()

    def toggle_pause(self) -> None:
        """Space bar / Play button: pause (leaving markers) or carry on."""
        if not self.paused:
            self._pause_here()
        elif self.finished:
            self.restart()
        else:
            self.paused = False

    def step_forward(self) -> None:
        """Right arrow: move to the next multiple of the pause interval and pause."""
        self.t = min(next_pause_time(self.t, self.pause_interval), self.end_time)
        self._pause_here()

    def jump_to(self, t: float) -> None:
        """Jump box: go to exactly time t, pause, and leave markers."""
        self.t = self._clamp(t)
        self._pause_here()

    def scrub_to(self, t: float) -> None:
        """Time slider: go to time t and pause, without leaving markers."""
        self.t = self._clamp(t)
        self.paused = True
        self._update_next_stop()

    def set_auto_pause(self, on: bool, interval: Optional[float] = None) -> None:
        """Turn auto-pause on or off (and optionally change its spacing) at any time."""
        self.auto_pause = on
        if interval is not None:
            self.pause_interval = interval
        self._update_next_stop()

    def set_visible(self, i: int, on: bool) -> None:
        """Show or hide path i right away (its flight is already stored)."""
        self.visible[i] = on
        if self.t > self.end_time:
            self.t = self.end_time
            self.paused = True
        self._update_next_stop()

    def clear_marks(self) -> None:
        self.marks = []

    def restart(self) -> None:
        """Back to t = 0 and playing. Markers are kept."""
        self.t = 0.0
        self.paused = False
        self._update_next_stop()

    def set_flights(self, flights: List[Flight], visible: Optional[List[bool]] = None) -> None:
        """Use new flights (after Play is pressed) and start from the beginning."""
        self.flights = list(flights)
        self.visible = list(visible) if visible is not None else [True] * len(self.flights)
        self.restart()

    # --- helpers ------------------------------------------------------------

    def _clamp(self, t: float) -> float:
        return max(0.0, min(t, self.end_time))

    def _pause_here(self, next_stop: Optional[float] = None) -> None:
        self.paused = True
        for i, on in enumerate(self.visible):
            if not on or self.flights[i].flight_time < self.t - _EPS:
                continue  # hidden, or already landed before this moment
            already = any(m[0] == i and abs(m[3] - self.t) < _EPS for m in self.marks)
            if not already:
                s = self.state(i)
                self.marks.append((i, s.x, s.y, self.t))
        self._update_next_stop(next_stop)

    def _update_next_stop(self, next_stop: Optional[float] = None) -> None:
        if not self.auto_pause:
            self._next_stop: Optional[float] = None
        elif next_stop is not None:
            self._next_stop = next_stop
        else:
            self._next_stop = next_pause_time(self.t, self.pause_interval)
