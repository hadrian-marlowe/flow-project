"""Tests for the launcher that `make run` uses."""

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402

from src.flow_project.main import load_simulation  # noqa: E402


def test_load_simulation_finds_ball_no_air():
    module = load_simulation("ball_no_air")
    assert callable(module.main)


def test_load_simulation_unknown_name():
    with pytest.raises(ModuleNotFoundError):
        load_simulation("does_not_exist")
