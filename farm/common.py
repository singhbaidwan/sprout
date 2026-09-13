"""Shared validation primitives for independent simulation systems."""


class GameError(ValueError):
    """An actionable player-facing error."""


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise GameError(f"Invalid {label}: expected an integer from {low} to {high}.")
    return value
