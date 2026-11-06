"""Tests for the projectile physics engine.

The big idea: the simulation steps forward in tiny time slices, and we check
it against the exact textbook formulas for a ball under gravity.
"""

import math

import numpy as np
import pytest

from src.flow_project.projectile import (
    Flight,
    exact_flight_time,
    exact_position,
    exact_velocity,
    simulate,
    step,
)


def test_step_changes_velocity_then_position():
    # one slice: vy drops by g*dt, then position moves with the NEW velocity
    x, y, vx, vy = step(0.0, 0.0, 3.0, 4.0, dt=0.1, g=10.0)
    assert vx == pytest.approx(3.0)
    assert vy == pytest.approx(3.0)
    assert x == pytest.approx(0.3)
    assert y == pytest.approx(0.3)


def test_exact_formulas_at_known_point():
    # 20 m/s at 45°: vx = vy = 14.142...; after 1 s with g=9.8
    x, y = exact_position(1.0, 20.0, 45.0, g=9.8)
    vx, vy = exact_velocity(1.0, 20.0, 45.0, g=9.8)
    assert x == pytest.approx(14.1421, abs=1e-3)
    assert y == pytest.approx(14.1421 - 4.9, abs=1e-3)
    assert vx == pytest.approx(14.1421, abs=1e-3)
    assert vy == pytest.approx(14.1421 - 9.8, abs=1e-3)


def test_exact_flight_time_flat_ground():
    # t = 2 v sin(a) / g
    assert exact_flight_time(20.0, 45.0, g=9.8) == pytest.approx(
        2 * 20 * math.sin(math.radians(45)) / 9.8
    )


def test_exact_flight_time_with_start_height():
    # dropped from 10 m with no speed: t = sqrt(2h/g)
    assert exact_flight_time(0.0, 0.0, g=9.8, start_height=10.0) == pytest.approx(
        math.sqrt(20 / 9.8)
    )


def test_simulate_matches_exact_formulas():
    flight = simulate(20.0, 45.0, g=9.8, start_height=0.0, dt=0.001)
    tol = 0.01 * flight.range
    for t_check in (0.5, 1.0, 1.5, 2.0):
        i = flight.index_at_time(t_check)
        ex, ey = exact_position(flight.t[i], 20.0, 45.0)
        evx, evy = exact_velocity(flight.t[i], 20.0, 45.0)
        assert flight.x[i] == pytest.approx(ex, abs=tol)
        assert flight.y[i] == pytest.approx(ey, abs=tol)
        assert flight.vx[i] == pytest.approx(evx, abs=1e-6)
        assert flight.vy[i] == pytest.approx(evy, abs=1e-6)


def test_vx_never_changes():
    flight = simulate(20.0, 30.0)
    assert np.allclose(flight.vx, flight.vx[0])


def test_range_and_max_height_match_formulas():
    flight = simulate(20.0, 45.0, g=9.8)
    exact_range = 20.0 ** 2 * math.sin(math.radians(90)) / 9.8
    exact_hmax = (20.0 * math.sin(math.radians(45))) ** 2 / (2 * 9.8)
    assert flight.range == pytest.approx(exact_range, rel=0.01)
    assert flight.max_height == pytest.approx(exact_hmax, rel=0.01)
    assert flight.flight_time == pytest.approx(exact_flight_time(20.0, 45.0), rel=0.01)


def test_simulate_stops_at_ground():
    flight = simulate(20.0, 45.0)
    assert flight.y[-1] == pytest.approx(0.0, abs=1e-9)
    assert (flight.y >= -1e-9).all()
    assert len(flight.t) == len(flight.x) == len(flight.y) == len(flight.vx) == len(flight.vy)


def test_simulate_from_height_lands_on_ground():
    flight = simulate(10.0, 0.0, start_height=5.0)
    assert flight.y[0] == pytest.approx(5.0)
    assert flight.y[-1] == pytest.approx(0.0, abs=1e-9)
    assert flight.flight_time == pytest.approx(
        exact_flight_time(10.0, 0.0, start_height=5.0), rel=0.01
    )


def test_higher_gravity_shorter_range():
    assert simulate(20.0, 45.0, g=20.0).range < simulate(20.0, 45.0, g=9.8).range


def test_45_degrees_goes_farthest_on_flat_ground():
    r45 = simulate(20.0, 45.0).range
    assert r45 > simulate(20.0, 30.0).range
    assert r45 > simulate(20.0, 60.0).range


def test_straight_up_has_zero_vx():
    flight = simulate(20.0, 90.0)
    assert np.allclose(flight.vx, 0.0)
    assert flight.range == pytest.approx(0.0, abs=1e-6)
    assert flight.max_height > 0


def test_zero_length_flight_is_single_sample():
    flight = simulate(20.0, 0.0, start_height=0.0)
    assert len(flight.t) == 1
    assert flight.flight_time == 0.0


def test_bad_gravity_raises():
    with pytest.raises(ValueError):
        simulate(20.0, 45.0, g=0.0)
    with pytest.raises(ValueError):
        exact_flight_time(20.0, 45.0, g=-9.8)


def test_speed_property_and_index_at_time():
    flight = simulate(20.0, 45.0, dt=0.001)
    assert isinstance(flight, Flight)
    assert flight.speed[0] == pytest.approx(20.0)
    assert flight.index_at_time(-5.0) == 0
    assert flight.index_at_time(1e9) == len(flight.t) - 1
    i = flight.index_at_time(1.25)
    assert flight.t[i] == pytest.approx(1.25, abs=0.0005)
