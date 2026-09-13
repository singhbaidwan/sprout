"""Select explicitly versioned scenarios without changing classic save semantics."""

from .engine import Farm, GameError, validate_state
from .factory import Factory, validate_factory


def validate_game(raw):
    if isinstance(raw, dict) and raw.get("scenario") == "factory":
        return validate_factory(raw)
    if isinstance(raw, dict) and "scenario" in raw and raw["scenario"] != "classic":
        raise GameError("Unknown game chapter.")
    return validate_state(raw)


def create_game(state=None):
    if state is not None:
        state = validate_game(state)
    return Factory(state) if isinstance(state, dict) and state.get("scenario") == "factory" else Farm(state)
