"""Tests for Playback: one shared clock for one or two flights.

Playback has no drawing code in it, so every rule can be checked exactly.
"""

import pytest

from src.flow_project.player import PathState, Playback, next_pause_time
from src.flow_project.projectile import simulate


@pytest.fixture
def two():
    return [simulate(20.0, 45.0), simulate(20.0, 30.0, start_height=5.0)]


def test_next_pause_time():
    assert next_pause_time(0.0, 0.5) == pytest.approx(0.5)
    assert next_pause_time(0.49, 0.5) == pytest.approx(0.5)
    assert next_pause_time(0.5, 0.5) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        next_pause_time(0.0, 0.0)


def test_starts_at_zero_playing(two):
    p = Playback(two)
    assert p.t == 0.0 and not p.paused and not p.finished
    assert p.end_time == pytest.approx(max(f.flight_time for f in two))
    assert isinstance(p.state(0), PathState) and p.state(0).speed == pytest.approx(20.0)


def test_advance_moves_frame_dt(two):
    p = Playback(two, frame_dt=0.02)
    p.advance()
    p.advance()
    assert p.t == pytest.approx(0.04)
    assert p.state(0).t == pytest.approx(0.04, abs=0.0005)


def test_no_auto_pause_by_default_runs_to_end(two):
    p = Playback(two, frame_dt=0.02)
    for _ in range(10000):
        p.advance()
    assert p.finished and p.paused and p.t == pytest.approx(p.end_time)


def test_auto_pause_exact_multiples(two):
    p = Playback(two, frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    stops = []
    for _ in range(10000):
        if p.paused:
            stops.append(p.t)
            if p.finished:
                break
            p.toggle_pause()
        p.advance()
    assert stops[:4] == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert all(b > a for a, b in zip(stops, stops[1:]))


def test_pause_marks_each_visible_path(two):
    p = Playback(two)
    for _ in range(10):
        p.advance()
    p.toggle_pause()
    assert [m[0] for m in p.marks] == [0, 1]
    assert p.marks[0][3] == pytest.approx(p.t)
    p.toggle_pause()
    assert not p.paused and len(p.marks) == 2


def test_hidden_path_gets_no_mark(two):
    p = Playback(two, visible=[True, False])
    p.jump_to(1.0)
    assert [m[0] for m in p.marks] == [0]
    assert p.end_time == pytest.approx(two[0].flight_time)


def test_landed_path_stays_at_landing(two):
    i = min(range(len(two)), key=lambda k: two[k].flight_time)
    short = two[i]
    p = Playback(two)
    p.jump_to(short.flight_time + 0.3)
    s = p.state(i)
    assert s.landed and s.y == pytest.approx(0.0, abs=1e-9) and s.x == pytest.approx(short.x[-1])
    assert s.t == pytest.approx(short.flight_time)
    assert [m[0] for m in p.marks] == [1 - i]  # only the still-flying path got a mark


def test_step_jump_scrub(two):
    p = Playback(two, pause_interval=0.5)
    p.step_forward()
    assert p.paused and p.t == pytest.approx(0.5)
    p.jump_to(1.23)
    assert p.t == pytest.approx(1.23) and p.marks[-1][3] == pytest.approx(1.23)
    n = len(p.marks)
    p.scrub_to(2.0)
    assert p.t == pytest.approx(2.0) and p.paused and len(p.marks) == n
    p.jump_to(99.0)
    assert p.finished
    p.jump_to(-1.0)
    assert p.t == 0.0


def test_no_duplicate_marks_same_time(two):
    p = Playback(two)
    p.jump_to(1.0)
    p.toggle_pause()
    p.toggle_pause()
    assert len(p.marks) == 2


def test_resume_after_end_restarts_and_clear_marks(two):
    p = Playback(two)
    p.jump_to(99.0)
    p.toggle_pause()
    assert p.t == 0.0 and not p.paused
    p.jump_to(0.5)
    p.clear_marks()
    assert p.marks == []


def test_coarse_dt_reaches_end():
    p = Playback([simulate(20.0, 45.0, dt=0.05)], frame_dt=0.02, pause_interval=0.25, auto_pause=True)
    for _ in range(10000):
        if p.paused and not p.finished:
            p.toggle_pause()
        p.advance()
    assert p.finished


def test_set_flights_restarts(two):
    p = Playback(two)
    p.jump_to(1.0)
    p.set_flights([simulate(10.0, 60.0)])
    assert p.t == 0.0 and not p.paused and len(p.visible) == 1


def test_zero_length_flight_is_finished():
    p = Playback([simulate(20.0, 0.0)])
    assert p.finished and p.state(0).landed


def test_set_auto_pause_turns_it_on_mid_flight(two):
    p = Playback(two, frame_dt=0.02, auto_pause=False)
    for _ in range(10):
        p.advance()  # t = 0.2
    p.set_auto_pause(True, 0.25)
    while not p.paused:
        p.advance()
    assert p.t == pytest.approx(0.25)
    p.set_auto_pause(False)
    p.toggle_pause()
    for _ in range(10000):
        p.advance()
    assert p.finished


def test_advance_by_a_chosen_amount(two):
    p = Playback(two, frame_dt=0.02)
    p.advance(0.05)
    assert p.t == pytest.approx(0.05)


def test_set_visible_applies_at_once_and_clamps(two):
    p = Playback(two)
    longer = max(range(2), key=lambda k: two[k].flight_time)
    p.jump_to(p.end_time)
    p.set_visible(longer, False)
    assert p.visible[longer] is False
    assert p.t == pytest.approx(p.end_time)  # clock pulled back to the shown flight's end
