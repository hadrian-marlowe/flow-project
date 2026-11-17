"""Simulation 1: a ball thrown with no air resistance, two paths at once.

Run it with:  make run

A window opens with:
  - the path equation across the top, with your numbers in it
    (click a number to jump to its box)
  - the plot, with a time slider and Play / Step / pause-every / jump-to-t
    controls underneath
  - boxes on the right for Path A and Path B, gravity, and the axes
  - a readout table of both balls' numbers

Type new numbers and press Enter, then press Play ("Launch") to use them.
Space = Play / Pause. Right arrow = Step.

The numbers below are only what the boxes start with. You can change
everything on screen, so you never have to edit this file to experiment.

Where the physics is:
  - src/flow_project/projectile.py   lines marked `# PHYSICS:` (the time-slice loop)
  - src/flow_project/launch.py       lines marked `# PHYSICS:` (vx, vy <-> v0, θ)
"""

from src.flow_project.launch import Launch
from src.flow_project.launch_window import LaunchWindow

# ---------------------------------------------------------------------------
# SETTINGS — what the boxes show when the window opens
# ---------------------------------------------------------------------------

# Path A (blue). x0, y0 in m; v0 in m/s; angle_deg in degrees above the ground.
PATH_A = dict(x0=0.0, y0=0.0, v0=20.0, angle_deg=45.0)

# Path B (orange). Same meaning as Path A.
PATH_B = dict(x0=0.0, y0=5.0, v0=20.0, angle_deg=30.0)
PATH_B_ON = True  # False = start with only Path A showing

GRAVITY = 9.8  # m/s². Earth 9.8, Moon 1.6, Mars 3.7, Jupiter 24.8

# How the simulation runs
DT = 0.001  # s. Size of each tiny time slice. Smaller = more accurate.

# How the animation plays
FRAME_DT = 0.02  # s of simulated time shown per animation frame
PAUSE_INTERVAL = 0.5  # s. Spacing for "pause every" and for Step
AUTO_PAUSE = False  # True = start with "pause every" ticked
PLAYBACK_SPEED = 0.5  # 0.25, 0.5 or 1.0 (1.0 = real time)

# ---------------------------------------------------------------------------
# End of settings.
# ---------------------------------------------------------------------------


def build_window() -> LaunchWindow:
    """Make the window from the settings above (without showing it)."""
    return LaunchWindow(
        [Launch(**PATH_A), Launch(**PATH_B)],
        g=GRAVITY,
        dt=DT,
        frame_dt=FRAME_DT,
        pause_interval=PAUSE_INTERVAL,
        auto_pause=AUTO_PAUSE,
        playback_speed=PLAYBACK_SPEED,
        path_b_on=PATH_B_ON,
    )


def main(show: bool = True) -> LaunchWindow:
    """Build the window and, unless show is False, open it."""
    window = build_window()
    if show:
        window.run()
    return window


if __name__ == "__main__":
    main()
