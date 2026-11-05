"""Entry point for the flow project. Run with `make run`."""

from src.flow_project.math_utils import add, mean


def main() -> None:
    print(f"add(2, 3) = {add(2, 3)}")
    print(f"mean([1, 2, 3, 4]) = {mean([1, 2, 3, 4])}")


if __name__ == "__main__":
    main()
