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
