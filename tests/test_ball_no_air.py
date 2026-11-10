"""Tests for the runnable ball_no_air simulation file."""

import matplotlib

matplotlib.use("Agg")  # never open a window during tests

import pytest  # noqa: E402

from simulations.ball_no_air import ball_no_air as sim  # noqa: E402


def test_settings_exist_with_defaults():
    assert sim.LAUNCH_SPEED == 20.0 and sim.LAUNCH_ANGLE == 45.0 and sim.GRAVITY == 9.8
    assert sim.DT == 0.001 and sim.FRAME_DT == 0.02 and sim.PAUSE_INTERVAL == 0.5
    assert sim.AUTO_PAUSE is True and sim.PLAYBACK_SPEED == 0.5


def test_build_flight_uses_settings():
    flight = sim.build_flight()
    assert flight.speed[0] == pytest.approx(sim.LAUNCH_SPEED)
    assert flight.range > 0


def test_main_without_show_builds_animation():
    anim = sim.main(show=False)
    assert anim.player.t == 0.0
    anim.draw_frame(0)
