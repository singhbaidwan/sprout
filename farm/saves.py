"""Validate portable saves and migrate the original single-farm envelope."""

from .engine import GameError, validate_state


def validate_save(raw):
    if not isinstance(raw, dict):
        raise GameError("Expected a Sprout save object.")
    if type(raw.get("version")) is int and raw["version"] == 1:
        raw = {"format": "sprout-save", "version": 2, "active": "classic", "games": {"classic": raw}}
    if raw.get("format") != "sprout-save" or type(raw.get("version")) is not int or raw["version"] != 2:
        raise GameError("This save format or version is not supported.")
    games = raw.get("games")
    if not isinstance(games, dict) or not games or set(games) - {"classic"}:
        raise GameError("The save contains an unknown or missing chapter.")
    active = raw.get("active")
    if type(active) is not str or active not in games:
        raise GameError("The active chapter is missing.")
    clean = {"format": "sprout-save", "version": 2, "active": active, "games": {}}
    for name, game in games.items():
        if not isinstance(game, dict):
            raise GameError("A saved chapter must be an object.")
        code, speed = game.get("code"), game.get("speed")
        if type(code) is not str or len(code) > 16000:
            raise GameError("Saved programs must be text under 16,000 characters.")
        if type(speed) is not str or speed not in ("1", "2", "4", "8"):
            raise GameError("Invalid playback speed in this save.")
        clean["games"][name] = {"state": validate_state(game.get("state")), "code": code, "speed": speed}
    return clean
