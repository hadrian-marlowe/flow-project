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


def test_plain_name_loads_the_final_version():
    module = load_simulation("ball_no_air")
    assert module.__name__ == "simulations.final.ball_no_air.ball_no_air"


def test_prototypes_prefix_loads_a_draft():
    module = load_simulation("prototypes/ball_no_air_v1")
    assert module.__name__ == "simulations.prototypes.ball_no_air_v1.ball_no_air_v1"
    assert callable(module.main)
