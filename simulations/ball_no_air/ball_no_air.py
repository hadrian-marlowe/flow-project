"""Simulation 1: a ball thrown with no air resistance.

Run it with:  make run            (or: make run SIM=ball_no_air)

Change the settings below, save, and run again to see how the flight changes.
The physics itself lives in src/flow_project/projectile.py (look for the lines
marked `# PHYSICS:`). The drawing lives in src/flow_project/animate.py.

Controls while the window is open:
  space        pause / resume (leaves a grey ghost marker)
  right arrow  step forward by PAUSE_INTERVAL seconds
  jump box     type an exact time in seconds and press Enter
"""

from src.flow_project.animate import FlightAnimation
from src.flow_project.player import Player
from src.flow_project.projectile import Flight, simulate

# ---------------------------------------------------------------------------
# SETTINGS — change these!
# ---------------------------------------------------------------------------

# How the ball is launched
LAUNCH_SPEED = 20.0  # m/s. How fast the ball leaves your hand.
LAUNCH_ANGLE = 45.0  # degrees above the ground. 90 = straight up, 0 = flat.
START_HEIGHT = 0.0  # m. Height above the ground where the ball starts.

# The world
GRAVITY = 9.8  # m/s². Earth is 9.8. Try the Moon (1.6) or Jupiter (24.8).

# How the simulation runs
DT = 0.001  # s. Size of each tiny time slice. Smaller = more accurate, slower.

# How the animation plays
FRAME_DT = 0.02  # s of simulated time shown per animation frame.
PLAYBACK_SPEED = 0.5  # 1.0 = real time, 0.5 = half speed, 2.0 = double speed.
PAUSE_INTERVAL = 0.5  # s. Auto-pause spacing, and how far the right arrow steps.
AUTO_PAUSE = True  # True = pause by itself every PAUSE_INTERVAL seconds.

# ---------------------------------------------------------------------------
# End of settings. Below here is the code that uses them.
# ---------------------------------------------------------------------------


def build_flight() -> Flight:
    """Run the physics for the whole flight using the settings above."""
    return simulate(
        speed=LAUNCH_SPEED,
        angle_deg=LAUNCH_ANGLE,
        g=GRAVITY,
        start_height=START_HEIGHT,
        dt=DT,
    )


def build_player(flight: Flight) -> Player:
    """Set up playback (pause, step, jump) using the settings above."""
    return Player(
        flight,
        frame_dt=FRAME_DT,
        pause_interval=PAUSE_INTERVAL,
        auto_pause=AUTO_PAUSE,
    )


def main(show: bool = True) -> FlightAnimation:
    """Build everything and, unless show is False, open the window."""
    flight = build_flight()
    player = build_player(flight)
    animation = FlightAnimation(flight, player, playback_speed=PLAYBACK_SPEED)
    print("Range: {:.1f} m   Max height: {:.1f} m   Flight time: {:.2f} s".format(
        flight.range, flight.max_height, flight.flight_time
    ))
    if show:
        animation.run()
    return animation


if __name__ == "__main__":
    main()
