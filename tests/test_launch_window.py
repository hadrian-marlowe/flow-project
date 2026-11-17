"""Tests for LaunchWindow, the on-screen controls.

Built with matplotlib's "Agg" backend, so no window ever opens during tests.
Buttons and boxes are driven by calling their handlers directly.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402
from matplotlib.backend_bases import MouseEvent, PickEvent  # noqa: E402

from src.flow_project.launch import Launch  # noqa: E402
from src.flow_project.launch_window import LaunchWindow  # noqa: E402


class Key:
    def __init__(self, key):
        self.key = key
        self.inaxes = None


@pytest.fixture
def win():
    w = LaunchWindow([Launch(), Launch(y0=5.0, angle_deg=30.0)])
    yield w
    plt.close(w.fig)


def test_window_builds_with_two_paths_and_defaults(win):
    assert len(win.playback.flights) == 2
    assert win.boxes[(0, "v0")].text == "20" and win.boxes[(1, "y0")].text == "5"
    assert win.g_box.text == "9.8" and not win.playback.paused
    assert win.boxes[(0, "vx")].text == "14.1"


def test_submitting_vx_rewrites_v0_and_angle(win):
    win.on_box_submit(0, "vx", "20")
    assert win.boxes[(0, "angle_deg")].text == "35.3"
    assert win.boxes[(0, "v0")].text == "24.5"
    assert win.launches[0].vx == pytest.approx(20.0)


def test_submitting_angle_rewrites_components(win):
    win.on_box_submit(0, "angle_deg", "60")
    assert win.boxes[(0, "vx")].text == "10.0" and win.boxes[(0, "vy")].text == "17.3"


def test_bad_number_in_a_box_is_rejected(win):
    win.on_box_submit(0, "v0", "fast")
    assert "number" in win.status_text.get_text()
    assert win.boxes[(0, "v0")].text == "20" and win.launches[0].v0 == pytest.approx(20.0)


def test_changes_apply_only_on_play(win):
    win.on_box_submit(0, "v0", "30")
    assert win.playback.flights[0].speed[0] == pytest.approx(20.0)
    assert win.play_button.label.get_text() == "Launch"
    win.on_play()
    assert win.playback.flights[0].speed[0] == pytest.approx(30.0) and win.playback.t == 0.0
    assert win.play_button.label.get_text() == "Pause"


class FakeClock:
    """Stands in for the computer's clock so tests know exactly how much time passed."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_tick_advances_by_real_time_times_speed(win):
    clock = FakeClock()
    win.clock = clock
    win.tick(0)  # first tick just starts the stopwatch
    for i in range(5):
        clock.now += 0.04  # 40 ms of real time per frame
        win.tick(i)
    assert win.playback.t == pytest.approx(5 * 0.04 * 0.5)  # speed 0.5×
    win.set_speed("1×")
    clock.now += 0.04
    win.tick(6)
    assert win.playback.t == pytest.approx(0.10 + 0.04)
    assert "t = 0.14 s" in win.plot.clock_text.get_text()
    assert "vx" in win.readout_text.get_text()
    assert win.slider.val == pytest.approx(0.14 / win.playback.end_time, abs=1e-3)


def test_space_toggles_and_right_steps(win):
    win.on_key(Key(" "))
    assert win.playback.paused and len(win.playback.marks) == 2
    win.on_key(Key(" "))
    assert not win.playback.paused
    win.on_key(Key("right"))
    assert win.playback.paused and win.playback.t == pytest.approx(0.5)


def test_space_ignored_while_typing(win):
    win.boxes[(0, "v0")].begin_typing()
    win.on_key(Key(" "))
    assert not win.playback.paused
    win.boxes[(0, "v0")].stop_typing()


def test_enter_in_box_ends_typing(win):
    box = win.boxes[(0, "vx")]
    box.begin_typing()
    box.set_val("15")
    box._observers.process("submit", box.text)  # what Enter does
    assert not box.capturekeystrokes
    assert win.launches[0].vx == pytest.approx(15.0)


def test_jump_box_and_go(win):
    win.on_jump("1.25")
    assert win.playback.t == pytest.approx(1.25) and win.playback.paused
    win.on_jump("abc")
    assert win.playback.t == pytest.approx(1.25)
    assert "number" in win.status_text.get_text()


def test_bad_input_shows_status_and_keeps_old_flight(win):
    win.on_jump("1.0")
    win.g_box.set_val("0")
    win.on_play()
    assert win.status_text.get_text() == "gravity must be a positive number"
    # the old flight is kept, exactly where it was (Play just resumed it)
    assert win.playback.t == pytest.approx(1.0) and win.g == pytest.approx(9.8)
    win.g_box.set_val("9.8")
    win.on_play()
    assert win.status_text.get_text() == ""


def test_negative_start_height_is_rejected_on_play(win):
    win.on_box_submit(1, "y0", "-3")
    win.on_play()
    assert win.status_text.get_text() == "Path B: start height can't be below the ground"


def test_preset_fills_g_box(win):
    win.apply_preset("Moon")
    assert win.g_box.text == "1.6" and win.g == pytest.approx(9.8)  # not applied until Play
    win.on_play()
    assert win.g == pytest.approx(1.6)


def test_axis_boxes_and_autofit(win):
    win.xmax_box.set_val("100")
    win.on_axis_submit()
    assert win.axes_edited and win.ax.get_xlim()[1] == pytest.approx(100)
    win.on_box_submit(0, "v0", "25")
    win.on_play()
    assert win.ax.get_xlim()[1] == pytest.approx(100)  # the student's axes are respected
    win.on_autofit()
    assert win.ax.get_xlim()[1] < 100 and not win.axes_edited


def test_bad_axis_box_is_rejected(win):
    win.xmin_box.set_val("500")
    win.on_axis_submit()
    assert win.status_text.get_text() == "x max must be bigger than x min"
    assert win.ax.get_xlim()[0] < 500


def test_path_b_checkbox_hides_second_ball(win):
    win.set_path_b(False)
    win.on_play()
    win.tick(0)
    assert not win.plot.balls[1].get_visible() and win.playback.visible == [True, False]


def test_auto_pause_checkbox_and_interval(win):
    clock = FakeClock()
    win.clock = clock
    win.interval_box.set_val("0.25")
    win.set_auto_pause(True)
    for i in range(100):
        clock.now += 0.04
        win.tick(i)
        if win.playback.paused:
            break
    assert win.playback.t == pytest.approx(0.25)


def test_equation_click_begins_typing_in_matching_box(win):
    mouse = MouseEvent("button_press_event", win.fig.canvas, 0, 0)
    win.on_pick(PickEvent("pick_event", win.fig.canvas, mouse, win.equation_pieces["v0"]))
    assert win.boxes[(0, "v0")].capturekeystrokes
    win.boxes[(0, "v0")].stop_typing()
    win.select_path(1)
    assert "30" in win.equation_pieces["angle_deg"].get_text()


def test_equation_shows_new_numbers_before_play(win):
    win.on_box_submit(0, "x0", "3")
    assert "3" in win.equation_pieces["x0"].get_text()


def test_scrub_pauses_without_marks(win):
    win.on_scrub(0.5)
    assert win.playback.paused and win.playback.marks == []
    assert win.playback.t == pytest.approx(0.5 * win.playback.end_time)


def test_clear_markers(win):
    win.on_jump("1.0")
    win.on_clear()
    assert win.playback.marks == []


def test_show_toggles(win):
    win.set_show("arrows", False)
    win.tick(0)
    assert not win.plot.vx_arrows[0].get_visible()


def test_no_cursor_shown_in_boxes_nobody_is_typing_in(win):
    win.on_box_submit(0, "vx", "20")
    assert not win.boxes[(0, "v0")].cursor.get_visible()
    assert not win.xmax_box.cursor.get_visible()


def test_real_click_on_equation_number_focuses_its_box(win):
    # A real click goes to every widget, not just the equation: press, then release.
    renderer = win.fig.canvas.get_renderer()
    piece = win.equation_pieces["y0"]
    box = piece.get_window_extent(renderer)
    x, y = box.x0 + box.width / 2, box.y0 + box.height / 2
    MouseEvent("button_press_event", win.fig.canvas, x, y, button=1)._process()
    MouseEvent("button_release_event", win.fig.canvas, x, y, button=1)._process()
    assert win.boxes[(0, "y0")].capturekeystrokes
    win.boxes[(0, "y0")].stop_typing()


# --- review fixes -------------------------------------------------------------


def test_nan_and_huge_numbers_are_refused(win):
    win.on_box_submit(0, "v0", "nan")
    assert "number" in win.status_text.get_text() and win.launches[0].v0 == pytest.approx(20.0)
    win.on_box_submit(0, "v0", "1000000")
    win.on_play()
    assert "too long" in win.status_text.get_text()
    assert win.playback.flights[0].speed[0] == pytest.approx(20.0)  # old flight kept


def test_matplotlib_shortcut_keys_are_switched_off():
    from src.flow_project.launch_window import disable_matplotlib_shortcuts
    with matplotlib.rc_context():
        disable_matplotlib_shortcuts()
        keymaps = {k: v for k, v in matplotlib.rcParams.items() if k.startswith("keymap.")}
        assert keymaps and all(v == [] for v in keymaps.values())


def test_a_click_on_empty_space_redraws_at_most_once(win):
    draws = []
    real_draw = win.fig.canvas.draw
    win.fig.canvas.draw = lambda *a, **k: (draws.append(1), real_draw(*a, **k))
    MouseEvent("button_press_event", win.fig.canvas, 5, 5, button=1)._process()
    MouseEvent("button_release_event", win.fig.canvas, 5, 5, button=1)._process()
    win.on_box_submit(0, "vx", "12")  # rewrites six boxes
    assert len(draws) <= 1


def test_play_still_pauses_after_a_launch_error(win):
    win.g_box.set_val("0")
    win.on_play()
    assert "gravity" in win.status_text.get_text()
    assert win.playback.paused
    win.on_play()
    assert not win.playback.paused


def test_path_b_checkbox_hides_and_shows_at_once(win):
    win.set_path_b(False)
    win.tick(0)
    assert win.playback.visible == [True, False] and not win.plot.balls[1].get_visible()
    assert win.play_button.label.get_text() != "Launch"
    win.set_path_b(True)
    win.tick(1)
    assert win.plot.balls[1].get_visible()


def test_clicking_an_equation_number_empties_its_box_for_typing(win):
    mouse = MouseEvent("button_press_event", win.fig.canvas, 0, 0)
    win.on_pick(PickEvent("pick_event", win.fig.canvas, mouse, win.equation_pieces["v0"]))
    box = win.boxes[(0, "v0")]
    assert box.text == ""
    box.stop_typing()  # clicked away without typing anything
    assert box.text == "20" and win.status_text.get_text() == ""
