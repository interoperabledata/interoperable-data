import sys


class RunnerError(Exception):
    """User-facing error with message already suitable for display."""
    pass


def print_info(msg: str) -> None:
    print(msg)


def print_error(msg: str) -> None:
    print(msg, file=sys.stderr)
