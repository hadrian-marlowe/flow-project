"""Tests for the runnable ball_no_air simulation file."""

import matplotlib

matplotlib.use("Agg")  # never open a window during tests

import pytest  # noqa: E402

from simulations.ball_no_air import ball_no_air as sim  # noqa: E402


def test_settings_are_sensible():
    # Not pinned to exact values: the whole point is that you change them.
    # These checks catch settings that would break the run.
    assert sim.LAUNCH_SPEED >= 0
    assert 0 <= sim.LAUNCH_ANGLE <= 90
    assert sim.START_HEIGHT >= 0
    assert sim.GRAVITY > 0
    assert 0 < sim.DT
    assert sim.FRAME_DT > 0
    assert sim.PLAYBACK_SPEED > 0
    assert sim.PAUSE_INTERVAL > 0
    assert isinstance(sim.AUTO_PAUSE, bool)


def test_build_flight_uses_settings():
    flight = sim.build_flight()
    assert flight.speed[0] == pytest.approx(sim.LAUNCH_SPEED)
    assert flight.range > 0


def test_main_without_show_builds_animation():
    anim = sim.main(show=False)
    assert anim.player.t == 0.0
    anim.draw_frame(0)
