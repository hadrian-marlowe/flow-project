"""Tests for Launch: one path's starting numbers with the linked velocity boxes."""

import math

import pytest

from src.flow_project.launch import Launch, parse_number, validate_launch, validate_world


def test_components_from_polar():
    launch = Launch(v0=20.0, angle_deg=45.0)
    assert launch.vx == pytest.approx(14.1421, abs=1e-3)
    assert launch.vy == pytest.approx(14.1421, abs=1e-3)


def test_set_components_updates_polar():
    launch = Launch(v0=20.0, angle_deg=45.0)
    launch.set_components(20.0, 14.142135)  # push vx up, keep vy: angle drops
    assert launch.v0 == pytest.approx(math.hypot(20.0, 14.142135))
    assert launch.angle_deg == pytest.approx(math.degrees(math.atan2(14.142135, 20.0)))
    assert launch.vx == pytest.approx(20.0) and launch.vy == pytest.approx(14.142135)


def test_round_trip_is_stable():
    launch = Launch(v0=17.3, angle_deg=28.0)
    launch.set_components(launch.vx, launch.vy)
    assert launch.v0 == pytest.approx(17.3, abs=1e-9)
    assert launch.angle_deg == pytest.approx(28.0, abs=1e-9)


def test_set_polar():
    launch = Launch()
    launch.set_polar(10.0, 90.0)
    assert launch.vx == pytest.approx(0.0, abs=1e-9) and launch.vy == pytest.approx(10.0)


def test_negative_components_give_angles_outside_0_90():
    launch = Launch()
    launch.set_components(-10.0, 10.0)
    assert launch.angle_deg == pytest.approx(135.0)
    launch.set_components(10.0, -5.0)
    assert launch.angle_deg < 0


def test_as_dict_keys():
    assert set(Launch().as_dict()) == {"x0", "y0", "v0", "angle_deg", "vx", "vy"}


@pytest.mark.parametrize(
    "text,expected",
    [("1.25", 1.25), (" 2 ", 2.0), ("-3", -3.0), ("", None), ("abc", None), ("1,25", None)],
)
def test_parse_number(text, expected):
    assert parse_number(text) == expected


def test_validate_messages():
    assert validate_launch(Launch()) is None
    assert validate_launch(Launch(y0=-3.0)) == "start height can't be below the ground"
    assert validate_launch(Launch(v0=-1.0)) == "speed can't be negative"
    assert validate_world(9.8, 0, 45, 0, 15) is None
    assert validate_world(0.0, 0, 45, 0, 15) == "gravity must be a positive number"
    assert validate_world(9.8, 45, 45, 0, 15) == "x max must be bigger than x min"
    assert validate_world(9.8, 0, 45, 20, 15) == "y max must be bigger than y min"


# --- review fixes -------------------------------------------------------------


@pytest.mark.parametrize("text", ["nan", "inf", "-inf", "1e400"])
def test_parse_number_rejects_non_finite(text):
    assert parse_number(text) is None


def test_flight_too_long_to_simulate_is_refused():
    from src.flow_project.launch import validate_flight_size
    assert validate_flight_size(Launch(v0=20.0), 9.8, 0.001) is None
    msg = validate_flight_size(Launch(v0=1e6), 9.8, 0.001)
    assert msg is not None and "too long" in msg
    assert validate_flight_size(Launch(v0=20.0), 0.0001, 0.001) is not None
