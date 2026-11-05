import pytest

from src.flow_project.math_utils import add, mean


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_mean():
    assert mean([1, 2, 3, 4]) == pytest.approx(2.5)
