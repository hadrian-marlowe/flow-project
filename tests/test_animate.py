"""Tests for the drawing code.

Everything is drawn with matplotlib's "Agg" backend, which draws to memory
instead of opening a window, so `make test` never pops anything up.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from src.flow_project.animate import (  # noqa: E402
    FlightPlot,
    auto_limits,
    format_readout_table,
    label_side,
)
from src.flow_project.launch import Launch  # noqa: E402
from src.flow_project.player import Playback  # noqa: E402
from src.flow_project.projectile import simulate  # noqa: E402

# --- helper functions ---------------------------------------------------------


def test_auto_limits_fit_both_flights():
    fl = [simulate(20.0, 45.0), simulate(20.0, 30.0, start_height=5.0)]
    xmin, xmax, ymin, ymax = auto_limits(fl)
    # a small margin below 0 so a ball sitting on the edge isn't cut in half
    assert -0.05 * xmax < xmin < 0 and -0.05 * ymax < ymin < 0
    assert xmax == pytest.approx(1.1 * max(f.x.max() for f in fl))
    assert ymax == pytest.approx(1.25 * max(f.y.max() for f in fl))


def test_auto_limits_negative_x():
    flight = simulate(20.0, 135.0)
    xmin, xmax, _, _ = auto_limits([flight])
    assert xmin == pytest.approx(1.1 * flight.x.min()) and 0 < xmax < 0.05 * abs(xmin)


def test_auto_limits_never_collapse():
    xmin, xmax, ymin, ymax = auto_limits([simulate(20.0, 90.0)])
    assert xmax - xmin >= 1.0 and xmin < 0 < xmax
    xmin, xmax, ymin, ymax = auto_limits([simulate(20.0, 0.0)])
    assert xmax - xmin >= 1.0 and ymax - ymin >= 1.0


def test_label_side_uses_visible_range():
    assert label_side(10.0, 0.0, 100.0) == "right"
    assert label_side(80.0, 0.0, 100.0) == "left"
    assert label_side(-5.0, -40.0, 0.0) == "left"


def test_format_readout_table():
    fl = [simulate(20.0, 45.0), None]
    p = Playback([fl[0]])
    p.jump_to(1.0)
    text = format_readout_table([p.state(0), None], fl, [0.0004, None])
    lines = text.splitlines()
    assert "A" in lines[0] and "B" in lines[0]
    assert any(line.startswith("vx") and "14.1" in line and "—" in line for line in lines)
    assert any(line.startswith("sim−eq") and "0.000" in line for line in lines)


# --- the plot -----------------------------------------------------------------


@pytest.fixture
def plot():
    launches = [Launch(), Launch(y0=5.0, angle_deg=30.0)]
    fl = [simulate(l.v0, l.angle_deg, start_height=l.y0, start_x=l.x0) for l in launches]
    pb = Playback(fl)
    fig, ax = plt.subplots(figsize=(8, 6))
    fp = FlightPlot(ax, pb, launches, 9.8)
    fp.set_limits(*auto_limits(fl))
    yield fp, pb
    plt.close(fig)


def test_two_balls_drawn_at_their_positions(plot):
    fp, pb = plot
    pb.jump_to(0.8)
    fp.draw()
    for i in range(2):
        x, y = fp.balls[i].get_data()
        assert float(x[0]) == pytest.approx(pb.state(i).x)
        assert float(y[0]) == pytest.approx(pb.state(i).y)
    assert "vx 14.1" in fp.label_texts[0][0].get_text()
    assert fp.clock_text.get_text() == "t = 0.80 s (paused)"


def test_hidden_path_is_invisible(plot):
    fp, pb = plot
    pb.visible[1] = False
    fp.draw()
    assert not fp.balls[1].get_visible() and not fp.trails[1].get_visible()
    assert fp.balls[0].get_visible()


def test_cross_matches_equation_and_gap_is_tiny(plot):
    fp, pb = plot
    pb.jump_to(1.2)
    fp.draw()
    assert fp.gap(0) < 0.01 * abs(pb.state(0).x) + 1e-6
    cx, _ = fp.crosses[0].get_data()
    assert float(cx[0]) == pytest.approx(pb.state(0).x, abs=0.05)


def test_landed_ball_stays_put(plot):
    fp, pb = plot
    short = min(range(2), key=lambda i: pb.flights[i].flight_time)
    pb.jump_to(pb.end_time)
    fp.draw()
    x, y = fp.balls[short].get_data()
    assert float(y[0]) == pytest.approx(0.0, abs=1e-9)
    assert float(x[0]) == pytest.approx(pb.flights[short].x[-1])


def test_arrows_equal_on_screen_for_equal_components(plot):
    fp, _ = plot
    fp.draw()
    to_px = fp.ax.transData.transform
    a, b = fp.vx_arrows[0], fp.vy_arrows[0]
    vx_len = abs(to_px(a.xy)[0] - to_px(a.xyann)[0])
    vy_len = abs(to_px(b.xy)[1] - to_px(b.xyann)[1])
    assert vx_len == pytest.approx(vy_len, rel=0.02) and vx_len > 20


def test_toggles_hide_arrows_and_labels(plot):
    fp, _ = plot
    fp.show_arrows = False
    fp.show_labels = False
    fp.draw()
    assert not fp.vx_arrows[0].get_visible() and not fp.label_texts[0][0].get_visible()


def test_marks_drawn_with_time_labels(plot):
    fp, pb = plot
    pb.jump_to(0.5)
    pb.toggle_pause()
    pb.jump_to(1.0)
    fp.draw()
    assert len(fp.marks_scatter.get_offsets()) == 4
    assert any(t.get_text() == "0.5s" for t in fp.mark_labels)
    pb.clear_marks()
    fp.draw()
    assert len(fp.marks_scatter.get_offsets()) == 0 and fp.mark_labels == []


def test_set_limits_applied(plot):
    fp, _ = plot
    fp.set_limits(-5, 50, 0, 30)
    assert fp.ax.get_xlim() == (-5, 50) and fp.ax.get_ylim() == (0, 30)


def test_straight_up_arrow_visible():
    launches = [Launch(angle_deg=90.0)]
    fl = [simulate(20.0, 90.0)]
    fig, ax = plt.subplots(figsize=(8, 6))
    fp = FlightPlot(ax, Playback(fl), launches, 9.8)
    fp.draw()
    ymin, ymax = ax.get_ylim()
    b = fp.vy_arrows[0]
    assert abs(b.xy[1] - b.xyann[1]) >= 0.05 * (ymax - ymin)
    plt.close(fig)


def test_labels_of_two_close_balls_do_not_overlap(plot):
    fp, pb = plot
    pb.jump_to(1.0)  # the two balls are close together here
    fp.draw()
    renderer = fp.ax.figure.canvas.get_renderer()
    boxes = [[t.get_window_extent(renderer) for t in fp.label_texts[i]] for i in range(2)]
    for a in boxes[0]:
        for b in boxes[1]:
            assert not a.overlaps(b)
