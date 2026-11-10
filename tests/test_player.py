"""Tests for Player: the playback rules (pause, step, auto-pause, jump, marks).

Player has no drawing code in it, so every rule can be checked exactly.
"""

import pytest

from src.flow_project.player import Player, next_pause_time
from src.flow_project.projectile import simulate


@pytest.fixture
def flight():
    return simulate(20.0, 45.0, dt=0.001)


def test_next_pause_time():
    assert next_pause_time(0.0, 0.5) == pytest.approx(0.5)
    assert next_pause_time(0.49, 0.5) == pytest.approx(0.5)
    assert next_pause_time(0.5, 0.5) == pytest.approx(1.0)
    assert next_pause_time(1.2, 0.25) == pytest.approx(1.25)
    with pytest.raises(ValueError):
        next_pause_time(0.0, 0.0)


def test_starts_at_beginning_playing(flight):
    p = Player(flight)
    assert p.index == 0 and p.t == 0.0 and not p.paused and not p.finished
    assert p.speed == pytest.approx(20.0)


def test_advance_moves_one_frame(flight):
    p = Player(flight, frame_dt=0.02, auto_pause=False)
    p.advance()
    assert p.t == pytest.approx(0.02, abs=0.0005)
    p.advance()
    assert p.t == pytest.approx(0.04, abs=0.0005)


def test_advance_does_nothing_when_paused(flight):
    p = Player(flight, auto_pause=False)
    p.toggle_pause()
    p.advance()
    assert p.t == 0.0


def test_auto_pause_lands_exactly_on_interval(flight):
    p = Player(flight, frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(0.25, abs=0.0005)
    assert p.marks[-1][2] == pytest.approx(0.25, abs=0.0005)
    p.toggle_pause()  # resume
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(0.5, abs=0.0005)
    assert len(p.marks) == 2


def test_space_pause_adds_mark_and_resume_does_not(flight):
    p = Player(flight, auto_pause=False)
    for _ in range(10):
        p.advance()
    p.toggle_pause()
    assert p.paused and len(p.marks) == 1
    assert p.marks[0][2] == pytest.approx(p.t)
    p.toggle_pause()
    assert not p.paused and len(p.marks) == 1


def test_step_forward(flight):
    p = Player(flight, pause_interval=0.5, auto_pause=False)
    p.step_forward()
    assert p.paused and p.t == pytest.approx(0.5, abs=0.0005)
    p.step_forward()
    assert p.t == pytest.approx(1.0, abs=0.0005)
    assert [round(m[2], 2) for m in p.marks] == [0.5, 1.0]


def test_step_forward_clamps_to_end(flight):
    p = Player(flight, pause_interval=100.0)
    p.step_forward()
    assert p.finished and p.t == pytest.approx(flight.flight_time)


def test_jump_to(flight):
    p = Player(flight)
    p.jump_to(1.25)
    assert p.paused
    assert p.t == pytest.approx(1.25, abs=0.0005)
    assert p.x == pytest.approx(flight.x[p.index])
    assert p.marks[-1] == (flight.x[p.index], flight.y[p.index], flight.t[p.index])


def test_jump_clamps(flight):
    p = Player(flight)
    p.jump_to(999.0)
    assert p.finished
    p.jump_to(-3.0)
    assert p.index == 0


def test_jump_then_resume_auto_pauses_at_next_interval(flight):
    p = Player(flight, frame_dt=0.02, pause_interval=0.5, auto_pause=True)
    p.jump_to(1.1)
    p.toggle_pause()
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(1.5, abs=0.0005)


def test_no_duplicate_mark_at_same_time(flight):
    p = Player(flight)
    p.jump_to(1.0)
    p.toggle_pause()  # resume
    p.toggle_pause()  # pause again at the same spot
    assert len(p.marks) == 1


def test_finishes_at_end(flight):
    p = Player(flight, auto_pause=False)
    for _ in range(10000):
        p.advance()
    assert p.finished and p.t == pytest.approx(flight.flight_time)


def test_zero_length_flight_is_finished_immediately():
    p = Player(simulate(20.0, 0.0))
    assert p.finished
    p.advance()
    assert p.index == 0


# --- coarse time steps must still play (review finding) ---------------------


def _play_to_end(p, max_frames=100000):
    for _ in range(max_frames):
        if p.finished:
            return True
        if p.paused:
            p.toggle_pause()
        p.advance()
    return p.finished


def test_coarse_dt_still_advances():
    # DT bigger than FRAME_DT: the nearest sample is the current one, but the
    # ball must still move forward one sample per frame.
    p = Player(simulate(20.0, 45.0, dt=0.05), frame_dt=0.02, auto_pause=False)
    p.advance()
    assert p.index == 1
    assert _play_to_end(p)


def test_coarse_dt_with_auto_pause_reaches_the_end():
    p = Player(simulate(20.0, 45.0, dt=0.03), frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    pause_times = []
    for _ in range(100000):
        if p.finished:
            break
        if p.paused:
            pause_times.append(p.t)
            p.toggle_pause()
        p.advance()
    assert p.finished
    # every pause is strictly later than the one before: no getting stuck
    assert all(b > a for a, b in zip(pause_times, pause_times[1:]))
    assert len(pause_times) >= 10


def test_step_forward_always_moves_with_coarse_dt():
    p = Player(simulate(20.0, 45.0, dt=0.2), pause_interval=0.1, auto_pause=False)
    p.step_forward()
    assert p.index == 1
