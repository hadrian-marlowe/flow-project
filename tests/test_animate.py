"""Tests for the animation code.

The helper functions are tested exactly. The drawing code is tested with
matplotlib's "Agg" backend, which draws to memory instead of opening a window.
"""

import pytest

from src.flow_project.animate import (
    axis_limits,
    format_readout,
    label_side,
    parse_jump_time,
)
from src.flow_project.projectile import simulate


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1.25", 1.25),
        (" 2 ", 2.0),
        ("0", 0.0),
        ("", None),
        ("abc", None),
        ("1,25", None),
        ("-2", None),
        ("999", 2.9),
    ],
)
def test_parse_jump_time(text, expected):
    assert parse_jump_time(text, flight_time=2.9) == expected


def test_axis_limits_fit_flight():
    flight = simulate(20.0, 45.0)
    xmax, ymax = axis_limits(flight)
    assert xmax == pytest.approx(flight.range * 1.1)
    assert ymax == pytest.approx(flight.max_height * 1.25)


def test_axis_limits_never_collapse():
    xmax, ymax = axis_limits(simulate(20.0, 90.0))  # straight up: range 0
    assert xmax >= 1.0
    xmax, ymax = axis_limits(simulate(20.0, 0.0))  # no flight at all
    assert xmax >= 1.0 and ymax >= 1.0


def test_label_side():
    assert label_side(10.0, 100.0) == "right"
    assert label_side(80.0, 100.0) == "left"


def test_format_readout():
    text = format_readout(
        t=1.234, x=10.0, y=5.55, vx=14.14, vy=-2.0, speed=14.28, max_height=10.2, rng=40.8
    )
    lines = text.splitlines()
    assert lines[0] == "t = 1.23 s"
    assert "x = 10.0 m" in lines
    assert "vy = -2.0 m/s" in lines
    assert "range = 40.8 m" in lines


# --- drawing code, tested without opening a window ---------------------------

import matplotlib

matplotlib.use("Agg")  # draw to memory, never open a window during tests

from src.flow_project.animate import FlightAnimation  # noqa: E402
from src.flow_project.player import Player  # noqa: E402


@pytest.fixture
def anim():
    flight = simulate(20.0, 45.0)
    player = Player(flight, frame_dt=0.02, pause_interval=0.5, auto_pause=True)
    return FlightAnimation(flight, player)


def test_first_frame_draws_ball_at_start(anim):
    anim.draw_frame(0)
    x, y = anim.ball.get_data()
    assert float(x[0]) == pytest.approx(anim.player.x)
    assert "vx 14.1" in anim.vx_text.get_text()
    assert anim.clock_text.get_text().startswith("t = ")


def test_frames_advance_and_update_labels(anim):
    for i in range(5):
        anim.draw_frame(i)
    assert anim.player.index > 0
    assert "t = {:.2f} s".format(anim.player.t) in anim.clock_text.get_text()
    assert "vy {:+.1f}".format(anim.player.vy) in anim.vy_text.get_text()
    assert len(anim.trail.get_xdata()) == anim.player.index + 1


def test_space_key_pauses_and_marks(anim):
    class Ev:
        key = " "
        inaxes = None

    anim.draw_frame(0)
    anim.draw_frame(1)
    anim.on_key(Ev())
    anim.draw_frame(2)
    assert anim.player.paused
    assert "(paused)" in anim.clock_text.get_text()
    assert len(anim.marks_scatter.get_offsets()) == 1


def test_right_key_steps_forward(anim):
    class Ev:
        key = "right"
        inaxes = None

    anim.on_key(Ev())
    anim.draw_frame(0)
    assert anim.player.t == pytest.approx(0.5, abs=0.0005)


def test_jump_box_moves_ball(anim):
    anim.on_jump("1.25")
    anim.draw_frame(0)
    assert anim.player.t == pytest.approx(1.25, abs=0.0005)
    assert "1.25" in anim.clock_text.get_text()
    anim.on_jump("garbage")
    assert anim.player.t == pytest.approx(1.25, abs=0.0005)


def test_readout_text_matches_player(anim):
    anim.on_jump("1.0")
    anim.draw_frame(0)
    assert "speed = {:.1f} m/s".format(anim.player.speed) in anim.readout_text.get_text()


def test_velocity_arrows_start_at_the_ball(anim):
    anim.on_jump("1.0")
    p = anim.player
    assert tuple(anim.vx_arrow.xyann) == pytest.approx((p.x, p.y))
    assert tuple(anim.vx_arrow.xy) == pytest.approx((p.x + p.vx * anim.arrow_scale, p.y))
    assert tuple(anim.vy_arrow.xyann) == pytest.approx((p.x, p.y))
    assert tuple(anim.vy_arrow.xy) == pytest.approx((p.x, p.y + p.vy * anim.arrow_scale))


def test_arrow_scale_auto_fits_the_plot():
    # With no arrow_scale given, the launch-speed arrow is ~15% of the plot width
    flight = simulate(20.0, 45.0)
    anim2 = FlightAnimation(flight, Player(flight))
    assert anim2.arrow_scale * flight.speed[0] == pytest.approx(0.15 * anim2.xmax)
    anim3 = FlightAnimation(flight, Player(flight), arrow_scale=0.5)
    assert anim3.arrow_scale == 0.5


def test_labels_sit_beyond_the_vx_arrow_head(anim):
    anim.on_jump("1.0")
    p = anim.player
    head_x = p.x + p.vx * anim.arrow_scale
    label_x = anim.vx_text.get_position()[0]
    assert label_x > head_x  # ball is in the left part of the plot, labels go right
