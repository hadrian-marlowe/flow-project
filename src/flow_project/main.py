"""Launcher for the simulations. `make run` calls this.

    make run                                runs the default final simulation (ball_no_air)
    make run SIM=ball_no_air                runs simulations/final/ball_no_air/ball_no_air.py
    make run SIM=prototypes/ball_no_air_v1  runs a rough draft from simulations/prototypes/
"""

import importlib
import sys
from types import ModuleType
from typing import List, Optional

DEFAULT_SIMULATION = "ball_no_air"


def load_simulation(name: str) -> ModuleType:
    """Import a simulation and return it as a module.

    "ball_no_air"              -> simulations/final/ball_no_air/ball_no_air.py
    "prototypes/ball_no_air_v1" -> simulations/prototypes/ball_no_air_v1/ball_no_air_v1.py
    """
    if name.startswith("prototypes/"):
        draft = name.split("/", 1)[1]
        return importlib.import_module("simulations.prototypes.{0}.{0}".format(draft))
    return importlib.import_module("simulations.final.{0}.{0}".format(name))


def main(argv: Optional[List[str]] = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    name = args[0] if args else DEFAULT_SIMULATION
    load_simulation(name).main()


if __name__ == "__main__":
    main()
