"""Pure, deterministic farm rules. All clock changes come from drone actions."""

from copy import deepcopy

CROPS = {
    "wheat": {"seed": 1, "sale": 5, "growth": 6, "unlock": 0},
    "carrot": {"seed": 3, "sale": 12, "growth": 9, "unlock": 40},
    "sunflower": {"seed": 5, "sale": 20, "growth": 12, "unlock": 100},
}
MISSIONS = [
    {"id": "first_harvest", "title": "A little honest work", "description": "Harvest 3 crops with your drone.", "stat": "harvested", "target": 3, "reward": 20},
    {"id": "plant_rows", "title": "Put down roots", "description": "Plant 12 crops. Let a loop do the work.", "stat": "planted", "target": 12, "reward": 25},
    {"id": "carrot_patch", "title": "Branch out", "description": "Unlock carrots and harvest 6 of them.", "stat": "carrots", "target": 6, "reward": 60},
    {"id": "automation", "title": "A farm that runs itself", "description": "Earn 200 coins from crop sales.", "stat": "earned", "target": 200, "reward": 100},
]
STAT_NAMES = ("harvested", "planted", "carrots", "earned", "actions")


class GameError(ValueError):
    """An actionable player-facing error."""


def empty_tile():
    return {"tilled": False, "crop": None, "growth": 0, "water": 0}


def new_state():
    state = {
        "version": 1, "size": 6, "tick": 0, "coins": 20,
        "drone": {"x": 0, "y": 0},
        "tiles": [empty_tile() for _ in range(36)],
        "unlocked": ["wheat"], "completed": [],
        "stats": {name: 0 for name in STAT_NAMES},
    }
    for x in range(3):
        state["tiles"][x] = {"tilled": True, "crop": "wheat", "growth": 6, "water": 0}
    return state


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise GameError(f"Invalid {label}: expected an integer from {low} to {high}.")
    return value


def validate_state(raw):
    """Rebuild, rather than trust, browser data. Unknown fields are discarded."""
    try:
        if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 1:
            raise GameError("This save version is not supported.")
        size = integer(raw["size"], 6, 8, "field size")
        if size not in (6, 8):
            raise GameError("Field size must be 6 or 8.")
        drone = raw["drone"]
        state = {
            "version": 1, "size": size,
            "tick": integer(raw["tick"], 0, 10**9, "tick"),
            "coins": integer(raw["coins"], 0, 10**9, "coins"),
            "drone": {axis: integer(drone[axis], 0, size - 1, "drone position") for axis in ("x", "y")},
            "stats": {key: integer(raw["stats"][key], 0, 10**9, key) for key in STAT_NAMES},
            "tiles": [],
        }
        unlocked = raw["unlocked"]
        if not isinstance(unlocked, list) or len(unlocked) > 3 or any(type(c) is not str or c not in CROPS for c in unlocked) or "wheat" not in unlocked:
            raise GameError("Invalid crop unlocks.")
        state["unlocked"] = list(dict.fromkeys(unlocked))
        completed = raw["completed"]
        if not isinstance(completed, list) or completed != [m["id"] for m in MISSIONS[:len(completed)]]:
            raise GameError("Invalid mission progress.")
        state["completed"] = list(completed)
        if any(state["stats"][m["stat"]] < m["target"] for m in MISSIONS[:len(completed)]):
            raise GameError("Mission progress does not match your statistics.")
        if not isinstance(raw["tiles"], list) or len(raw["tiles"]) != size * size:
            raise GameError("Invalid number of field tiles.")
        for tile in raw["tiles"]:
            crop = tile["crop"]
            if crop is not None and (type(crop) is not str or crop not in state["unlocked"]):
                raise GameError("Invalid saved crop.")
            if type(tile["tilled"]) is not bool or (crop and not tile["tilled"]):
                raise GameError("Invalid soil state.")
            growth = integer(tile["growth"], 0, CROPS[crop]["growth"] if crop else 0, "crop growth")
            water = integer(tile["water"], 0, 24, "moisture")
            state["tiles"].append({"tilled": tile["tilled"], "crop": crop, "growth": growth, "water": water})
        return state
    except (KeyError, TypeError, IndexError) as exc:
        raise GameError("This save is incomplete or malformed.") from exc


class Farm:
    missions = MISSIONS

    def __init__(self, state=None):
        self.state = validate_state(state) if state is not None else new_state()
        self.events = []

    @property
    def tile(self):
        s = self.state
        return s["tiles"][s["drone"]["y"] * s["size"] + s["drone"]["x"]]

    def snapshot(self):
        return deepcopy(self.state)

    def ready(self):
        tile = self.tile
        return bool(tile["crop"] and tile["growth"] >= CROPS[tile["crop"]]["growth"])

    def advance(self):
        s = self.state
        s["tick"] += 1
        s["stats"]["actions"] += 1
        for tile in s["tiles"]:
            if tile["water"]:
                if tile["crop"]:
                    tile["growth"] = min(CROPS[tile["crop"]]["growth"], tile["growth"] + 1)
                tile["water"] -= 1
        self.advance_systems()
        while len(s["completed"]) < len(self.missions):
            mission = self.missions[len(s["completed"])]
            if s["stats"][mission["stat"]] < mission["target"]:
                break
            s["completed"].append(mission["id"])
            s["coins"] += mission["reward"]
            self.events.append(f"Mission complete: {mission['title']}! +{mission['reward']} coins")

    def advance_systems(self):
        """Scenario hook: advance other systems once, before checking missions."""

    def action(self, name, *args):
        s, tile = self.state, self.tile
        self.events = []
        position = f"({s['drone']['x']}, {s['drone']['y']})"
        if name == "move":
            if len(args) != 1 or args[0] not in ("north", "south", "east", "west"):
                raise GameError('Use move("north"), "south", "east", or "west".')
            dx, dy = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[args[0]]
            s["drone"]["x"] = (s["drone"]["x"] + dx) % s["size"]
            s["drone"]["y"] = (s["drone"]["y"] + dy) % s["size"]
            message = f"Moved {args[0]} → ({s['drone']['x']}, {s['drone']['y']})"
        elif name == "plant":
            if len(args) != 1 or type(args[0]) is not str or args[0] not in CROPS:
                raise GameError('Choose plant("wheat"), plant("carrot"), or plant("sunflower").')
            crop = args[0]
            if crop not in s["unlocked"]:
                raise GameError(f"Unlock {crop} in the workshop first.")
            if tile["crop"]:
                raise GameError("This plot already has a crop. Harvest it when ready.")
            if not tile["tilled"]:
                raise GameError("This plot needs prepared soil. Call till() before plant().")
            price = CROPS[crop]["seed"]
            if s["coins"] < price and crop != "wheat":
                raise GameError(f"You need {price} coins to plant {crop}. Wheat can help you recover.")
            free = crop == "wheat" and s["coins"] == 0
            s["coins"] -= 0 if free else price
            tile.update(crop=crop, growth=0)
            s["stats"]["planted"] += 1
            message = f"Planted {crop} at {position}" + (" · emergency seed is free" if free else f" · −{price} coin{'s' if price != 1 else ''}")
        elif name in ("till", "water", "harvest", "wait"):
            if args:
                raise GameError(f"{name}() takes no arguments.")
            if name == "till":
                if tile["crop"]:
                    raise GameError("Harvest the existing crop before tilling this plot.")
                tile["tilled"] = True
                message = f"Prepared soil at {position}"
            elif name == "water":
                tile["water"] = 24
                message = f"Watered plot at {position}"
            elif name == "harvest":
                if not self.ready():
                    raise GameError("Nothing ripe here yet. Water your crop, then wait or work on other plots.")
                crop = tile["crop"]
                income = CROPS[crop]["sale"]
                s["coins"] += income
                s["stats"]["earned"] += income
                s["stats"]["harvested"] += 1
                s["stats"]["carrots"] += int(crop == "carrot")
                tile.update(crop=None, growth=0)
                message = f"Harvested {crop} at {position} · +{income} coins"
            else:
                message = "Waited one tick"
        else:
            raise GameError(f"Unknown drone action: {name}.")
        self.advance()
        return message

    def unlock(self, item):
        if item == "expansion":
            if self.state["size"] == 8:
                raise GameError("Your field is already expanded.")
            cost = 150
        elif type(item) is str and item in CROPS and item != "wheat":
            if item in self.state["unlocked"]:
                raise GameError(f"{item.title()} is already unlocked.")
            cost = CROPS[item]["unlock"]
        else:
            raise GameError("Unknown workshop upgrade.")
        if self.state["coins"] < cost:
            raise GameError(f"You need {cost} coins for this upgrade.")
        self.state["coins"] -= cost
        if item == "expansion":
            old = self.state["tiles"]
            self.state["tiles"] = [old[y * 6 + x] if x < 6 and y < 6 else empty_tile() for y in range(8) for x in range(8)]
            self.state["size"] = 8
        else:
            self.state["unlocked"].append(item)
        return f"Unlocked {item}!"
