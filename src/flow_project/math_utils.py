"""Small example utilities used to verify the project scaffolding."""

import numpy as np


def add(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def mean(values) -> float:
    """Return the arithmetic mean of a sequence of numbers."""
    return float(np.mean(values))
