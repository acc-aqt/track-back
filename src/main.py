"""Provide an exemplary entry point."""

from argparse import ArgumentParser
from example_package.example_module import my_sum


def entry_point():
    """Provide an exemplary entry point. Take two arguments and print their sum."""
    parser = ArgumentParser(description="A simple CLI.")

    parser.add_argument("input_one", type=float)
    parser.add_argument("input_two", type=float)

    args = parser.parse_args()
    print(my_sum(args.input_one, args.input_two))
