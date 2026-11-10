"""Launcher for the simulations. `make run` calls this.

    make run                    runs the default simulation (ball_no_air)
    make run SIM=ball_no_air    runs the simulation in simulations/<SIM>/<SIM>.py
"""

import importlib
import sys
from types import ModuleType
from typing import List, Optional

DEFAULT_SIMULATION = "ball_no_air"


def load_simulation(name: str) -> ModuleType:
    """Import simulations/<name>/<name>.py and return it as a module."""
    return importlib.import_module("simulations.{0}.{0}".format(name))


def main(argv: Optional[List[str]] = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    name = args[0] if args else DEFAULT_SIMULATION
    load_simulation(name).main()


if __name__ == "__main__":
    main()
