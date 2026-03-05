import logging
import sys
from argparse import ArgumentParser
from argparse import Namespace


class UserError(Exception):
    pass


def parse_args() -> Namespace:
    parser = ArgumentParser()

    return parser.parse_args()


def main() -> None:
    pass


def entry_point() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        main(**vars(parse_args()))
    except UserError as e:
        logging.error(f"error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error("Operation interrupted.")
        sys.exit(130)
