"""Tests for the runnable ball_no_air simulation file."""

import matplotlib

matplotlib.use("Agg")  # never open a window during tests

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from simulations.final.ball_no_air import ball_no_air as sim  # noqa: E402


def test_settings_are_sensible():
    # Not pinned to exact values: the whole point is that you change them.
    # These checks catch settings that would break the window.
    for path in (sim.PATH_A, sim.PATH_B):
        assert set(path) == {"x0", "y0", "v0", "angle_deg"}
        assert path["y0"] >= 0 and path["v0"] >= 0
    assert sim.GRAVITY > 0 and sim.DT > 0 and sim.FRAME_DT > 0 and sim.PAUSE_INTERVAL > 0
    assert sim.PLAYBACK_SPEED in (0.25, 0.5, 1.0)
    assert isinstance(sim.AUTO_PAUSE, bool) and isinstance(sim.PATH_B_ON, bool)


def test_build_window_uses_settings():
    w = sim.build_window()
    assert w.launches[0].v0 == pytest.approx(sim.PATH_A["v0"])
    assert w.launches[1].y0 == pytest.approx(sim.PATH_B["y0"])
    assert w.g == pytest.approx(sim.GRAVITY)
    assert w.playback.auto_pause is sim.AUTO_PAUSE
    plt.close(w.fig)


def test_main_without_show_returns_window():
    w = sim.main(show=False)
    w.tick(0)  # starts the stopwatch
    w.tick(1)
    assert w.playback.t > 0
    plt.close(w.fig)
