"""Breadworks: finite, single-drone logistics on a deterministic world clock."""

from collections import deque

from .engine import Farm, GameError, STAT_NAMES, empty_tile, integer, validate_state

ITEMS = ("wheat", "flour", "bread")
ENTITIES = {
    "chest": {"title": "Grain chest", "x": 0, "y": 6, "capacity": 48},
    "mill": {"title": "Mill", "x": 3, "y": 6, "ingredient": "wheat", "amount": 2, "product": "flour", "ticks": 4, "input_capacity": 12, "output_capacity": 8},
    "oven": {"title": "Oven", "x": 6, "y": 6, "ingredient": "flour", "amount": 1, "product": "bread", "ticks": 6, "input_capacity": 12, "output_capacity": 8},
    "depot": {"title": "Delivery depot", "x": 7, "y": 3, "price": 8},
}
OBSTACLES = ((6, 2), (6, 3), (3, 4))
UPGRADES = [
    {"id": "cargo", "title": "Bigger cargo", "detail": "Carry 16 items instead of 8", "cost": 50},
    {"id": "mill", "title": "Quick mill", "detail": "Mill a batch in 2 ticks", "cost": 75},
    {"id": "oven", "title": "Hotter oven", "detail": "Bake a loaf in 3 ticks", "cost": 90},
]
MISSIONS = [
    {"id": "first_flour", "title": "A different kind of grain", "description": "Mill 4 flour. Feed wheat into the mill and let it work.", "stat": "flour_milled", "target": 4, "reward": 15, "hint": "Run First bread. It carries 8 wheat from the chest into the mill."},
    {"id": "first_bread", "title": "Something in the oven", "description": "Bake 4 loaves using flour from the mill.", "stat": "bread_baked", "target": 4, "reward": 20, "hint": "Load flour at the mill, unload it at the oven, then wait for bread."},
    {"id": "first_delivery", "title": "Open for business", "description": "Deliver 4 bread to the depot. Each loaf sells for 8 coins.", "stat": "bread_delivered", "target": 4, "reward": 30, "hint": "Load bread at the oven, navigate_to(\"depot\"), and unload it."},
    {"id": "supply_field", "title": "From the ground up", "description": "Harvest 12 wheat plots. Each harvest puts 3 wheat in cargo.", "stat": "harvested", "target": 12, "reward": 40, "hint": "Run Harvest & store. It plants and waters all 24 growing plots. Run it again for ripe crops."},
    {"id": "twenty_loaves", "title": "The village bakery", "description": "Deliver 20 bread in total. Build a routine that restocks and processes grain.", "stat": "bread_delivered", "target": 20, "reward": 80, "hint": "Run Farm to bakery repeatedly. Buy cargo and machine upgrades when you can."},
    {"id": "fifty_loaves", "title": "An operation of your own", "description": "Deliver 50 bread in total. Then beat your delivery-order record.", "stat": "bread_delivered", "target": 50, "reward": 150, "hint": "Overlap milling and baking. Order runner can deliver 12 loaves in one finite run."},
]
FACTORY_STATS = STAT_NAMES + ("flour_milled", "bread_baked", "bread_delivered")
ORDER = {"target": 12, "deadline": 180, "reward": 40, "unlock": 4}
CATALOG = {"entities": ENTITIES, "obstacles": OBSTACLES, "upgrades": UPGRADES,
           "field": {"width": 6, "height": 4}, "cargo_capacity": 8, "harvest_yield": 3, "order": ORDER}
DIRECTIONS = {"east": (1, 0), "south": (0, 1), "west": (-1, 0), "north": (0, -1)}


def inventory():
    return dict.fromkeys(ITEMS, 0)


def new_factory():
    state = {
        "version": 2, "scenario": "factory", "size": 8, "tick": 0, "coins": 30,
        "drone": {"x": 0, "y": 0}, "tiles": [empty_tile() for _ in range(64)],
        "unlocked": ["wheat"], "completed": [], "stats": dict.fromkeys(FACTORY_STATS, 0),
        "cargo": inventory(), "chest": {"wheat": 12, "flour": 0, "bread": 0}, "upgrades": [],
        "machines": {name: {"input": 0, "output": 0, "remaining": 0} for name in ("mill", "oven")},
        "order": {"status": "idle", "start_tick": 0, "start_delivered": 0, "best": None, "completed": 0},
    }
    for x in range(4):
        state["tiles"][x] = {"tilled": True, "crop": "wheat", "growth": 6, "water": 0}
    return state


def walkable(x, y):
    return 0 <= x < 8 and 0 <= y < 8 and (x, y) not in OBSTACLES


def farmland(x, y):
    return 0 <= x < 6 and 0 <= y < 4


def validate_factory(raw):
    try:
        if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 2 or raw.get("scenario") != "factory":
            raise GameError("This Breadworks save version is not supported.")
        # Reuse soil/common-field validation without interpreting classic mission IDs.
        base = dict(raw, version=1, completed=[])
        state = validate_state(base)
        if state["size"] != 8 or state["unlocked"] != ["wheat"]:
            raise GameError("Breadworks needs its 8 × 8 wheat map.")
        if not walkable(**state["drone"]):
            raise GameError("The saved drone is on an obstacle.")
        for i, tile in enumerate(state["tiles"]):
            if not farmland(i % 8, i // 8) and tile != empty_tile():
                raise GameError("Crops and soil must stay inside the growing field.")
        upgrades = raw["upgrades"]
        if not isinstance(upgrades, list) or len(upgrades) > 3 or any(type(item) is not str or item not in ("cargo", "mill", "oven") for item in upgrades) or len(set(upgrades)) != len(upgrades):
            raise GameError("Invalid factory upgrades.")
        state.update(version=2, scenario="factory", upgrades=list(upgrades))
        for key, capacity in (("cargo", 16 if "cargo" in upgrades else 8), ("chest", 48)):
            state[key] = {item: integer(raw[key][item], 0, capacity, key) for item in ITEMS}
            if sum(state[key].values()) > capacity:
                raise GameError(f"Saved {key} exceeds its capacity.")
        state["machines"] = {}
        for name in ("mill", "oven"):
            machine, definition = raw["machines"][name], ENTITIES[name]
            # A purchased speed upgrade applies to the next batch, not an in-flight one.
            state["machines"][name] = {
                "input": integer(machine["input"], 0, definition["input_capacity"], "machine input"),
                "output": integer(machine["output"], 0, definition["output_capacity"], "machine output"),
                "remaining": integer(machine["remaining"], 0, definition["ticks"] - 1, "machine progress"),
            }
            if machine["remaining"] and machine["output"] == definition["output_capacity"]:
                raise GameError("A working machine must have room for its reserved output.")
        state["stats"] = {key: integer(raw["stats"][key], 0, 10**9, key) for key in FACTORY_STATS}
        completed = raw["completed"]
        if not isinstance(completed, list) or completed != [m["id"] for m in MISSIONS[:len(completed)]] or any(state["stats"][m["stat"]] < m["target"] for m in MISSIONS[:len(completed)]):
            raise GameError("Invalid factory mission progress.")
        state["completed"] = list(completed)
        order = raw["order"]
        if order["status"] not in ("idle", "active", "complete", "failed"):
            raise GameError("Invalid delivery order status.")
        state["order"] = {
            "status": order["status"], "start_tick": integer(order["start_tick"], 0, state["tick"], "order start"),
            "start_delivered": integer(order["start_delivered"], 0, state["stats"]["bread_delivered"], "order deliveries"),
            "completed": integer(order["completed"], 0, 10**9, "completed orders"),
            "best": None if order["best"] is None else integer(order["best"], 1, ORDER["deadline"], "best order time"),
        }
        elapsed = state["tick"] - order["start_tick"]
        delivered = state["stats"]["bread_delivered"] - order["start_delivered"]
        if order["status"] == "active" and (elapsed >= ORDER["deadline"] or delivered >= ORDER["target"]):
            raise GameError("This active order should already be resolved.")
        return state
    except (KeyError, TypeError, IndexError) as exc:
        raise GameError("This Breadworks save is incomplete or malformed.") from exc


class Factory(Farm):
    missions = MISSIONS

    def __init__(self, state=None):
        self.state = validate_factory(state) if state is not None else new_factory()
        self.events = []

    def cargo_space(self):
        return (16 if "cargo" in self.state["upgrades"] else 8) - sum(self.state["cargo"].values())

    def entity_here(self):
        return next((name for name, entity in ENTITIES.items() if all(self.state["drone"][axis] == entity[axis] for axis in ("x", "y"))), None)

    def machine_status(self, name):
        if type(name) is not str or name not in self.state["machines"]:
            raise GameError('Choose machine_status("mill") or machine_status("oven").')
        machine, definition = self.state["machines"][name], ENTITIES[name]
        if machine["remaining"]:
            return "working"
        if machine["output"] >= definition["output_capacity"]:
            return "output_full"
        return "waiting_input" if machine["input"] < definition["amount"] else "ready"

    def stored(self, entity, item):
        self.check_item(item)
        if type(entity) is not str or entity not in ENTITIES:
            raise GameError('Choose "chest", "mill", "oven", or "depot".')
        if entity == "chest":
            return self.state["chest"][item]
        if entity == "depot":
            return 0
        definition, machine = ENTITIES[entity], self.state["machines"][entity]
        if item == definition["ingredient"]:
            return machine["input"]
        if item == definition["product"]:
            return machine["output"]
        return 0

    def free_space(self, entity, item):
        self.check_item(item)
        if entity == "chest":
            return 48 - sum(self.state["chest"].values())
        if type(entity) is not str or entity not in ("mill", "oven"):
            raise GameError('Check free_space("chest", item), "mill", or "oven".')
        definition = ENTITIES[entity]
        return definition["input_capacity"] - self.state["machines"][entity]["input"] if item == definition["ingredient"] else 0

    @staticmethod
    def check_item(item):
        if type(item) is not str or item not in ITEMS:
            raise GameError('Choose "wheat", "flour", or "bread".')

    def route(self, *args):
        if len(args) == 1 and type(args[0]) is str and args[0] in ENTITIES:
            target = (ENTITIES[args[0]]["x"], ENTITIES[args[0]]["y"])
        elif len(args) == 2:
            target = tuple(integer(arg, 0, 7, "destination") for arg in args)
        else:
            raise GameError('Use navigate_to("chest"), "mill", "oven", "depot", or navigate_to(x, y).')
        if not walkable(*target):
            raise GameError("That destination is blocked by a rock.")
        start = (self.state["drone"]["x"], self.state["drone"]["y"])
        frontier, visited = deque([(start, [])]), {start}
        while frontier:
            point, route = frontier.popleft()
            if point == target:
                return route
            for direction, (dx, dy) in DIRECTIONS.items():
                next_point = (point[0] + dx, point[1] + dy)
                if next_point not in visited and walkable(*next_point):
                    visited.add(next_point)
                    frontier.append((next_point, route + [direction]))
        raise GameError("No route reaches that destination.")

    def advance_systems(self):
        s = self.state
        # Transfers happen first; every machine then advances exactly once.
        for name in ("mill", "oven"):
            machine, definition = s["machines"][name], ENTITIES[name]
            if not machine["remaining"] and machine["input"] >= definition["amount"] and machine["output"] < definition["output_capacity"]:
                machine["input"] -= definition["amount"]
                machine["remaining"] = definition["ticks"] // (2 if name in s["upgrades"] else 1)
            if machine["remaining"]:
                machine["remaining"] -= 1
                if not machine["remaining"]:
                    machine["output"] += 1
                    s["stats"]["flour_milled" if name == "mill" else "bread_baked"] += 1
        order = s["order"]
        if order["status"] == "active":
            elapsed = s["tick"] - order["start_tick"]
            if s["stats"]["bread_delivered"] - order["start_delivered"] >= ORDER["target"]:
                order["status"] = "complete"
                order["completed"] += 1
                order["best"] = min(order["best"] or elapsed, elapsed)
                s["coins"] += ORDER["reward"]
                self.events.append(f"Order complete in {elapsed} ticks! +{ORDER['reward']} coins")
            elif elapsed >= ORDER["deadline"]:
                order["status"] = "failed"
                self.events.append("Order expired. Your stock and deliveries are kept. Try another route!")

    def start_order(self):
        s = self.state
        if s["order"]["status"] == "active":
            raise GameError("An order is already running.")
        if s["stats"]["bread_delivered"] < ORDER["unlock"]:
            raise GameError("Deliver your first 4 bread to unlock timed orders.")
        s["order"].update(status="active", start_tick=s["tick"], start_delivered=s["stats"]["bread_delivered"])
        return "Order started: deliver 12 bread within 180 action ticks. Stockpiles count."

    def action(self, name, *args):
        s = self.state
        self.events = []
        if name == "move":
            if len(args) != 1 or type(args[0]) is not str or args[0] not in DIRECTIONS:
                raise GameError('Use move("north"), "south", "east", or "west".')
            dx, dy = DIRECTIONS[args[0]]
            x, y = s["drone"]["x"] + dx, s["drone"]["y"] + dy
            if not walkable(x, y):
                raise GameError("This route hits an edge or rock. Try navigate_to(x, y).")
            s["drone"].update(x=x, y=y)
            message = f"Moved {args[0]} → ({x}, {y})"
        elif name in ("load", "unload"):
            if len(args) != 2:
                raise GameError(f'Use {name}("wheat", amount), "flour", or "bread".')
            item, amount = args
            self.check_item(item)
            integer(amount, 1, 48, "transfer amount")
            entity = self.entity_here()
            if entity is None:
                raise GameError('Navigate onto a building pad before transferring cargo.')
            if name == "load":
                if amount > self.cargo_space():
                    raise GameError("Cargo is full. Unload items or request a smaller amount.")
                if amount > self.stored(entity, item):
                    raise GameError(f"Not enough {item} at {entity}.")
                if entity == "chest":
                    source, key = s["chest"], item
                elif entity in ("mill", "oven") and item == ENTITIES[entity]["product"]:
                    source, key = s["machines"][entity], "output"
                else:
                    raise GameError("Only finished products can be loaded from a machine.")
                source[key] -= amount
                s["cargo"][item] += amount
            else:
                if s["cargo"][item] < amount:
                    raise GameError(f"Your drone is not carrying {amount} {item}.")
                if entity == "depot":
                    if item != "bread":
                        raise GameError("The depot buys bread. Mill wheat into flour, then bake it.")
                    s["coins"] += amount * ENTITIES["depot"]["price"]
                    s["stats"]["earned"] += amount * ENTITIES["depot"]["price"]
                    s["stats"]["bread_delivered"] += amount
                else:
                    if self.free_space(entity, item) < amount:
                        raise GameError(f"Not enough input space for {item} at {entity}.")
                    if entity == "chest":
                        s["chest"][item] += amount
                    else:
                        s["machines"][entity]["input"] += amount
                s["cargo"][item] -= amount
            message = f"{'Loaded' if name == 'load' else 'Unloaded'} {amount} {item} at {entity}"
        elif name in ("harvest", "till", "plant", "water"):
            if not farmland(**s["drone"]):
                raise GameError("Grow crops in the field: x 0–5, y 0–3. Building pads are for cargo.")
            if name != "harvest":
                return super().action(name, *args)
            if args:
                raise GameError("harvest() takes no arguments.")
            if not self.ready():
                raise GameError("Nothing ripe here. Water wheat, then work elsewhere or wait().")
            if self.cargo_space() < 3:
                raise GameError('A harvest needs 3 cargo slots. Unload wheat at the chest or mill.')
            s["cargo"]["wheat"] += 3
            s["stats"]["harvested"] += 1
            self.tile.update(crop=None, growth=0)
            message = "Harvested 3 wheat into drone cargo"
        else:
            return super().action(name, *args)
        self.advance()
        return message

    def unlock(self, item):
        upgrade = next((entry for entry in UPGRADES if entry["id"] == item), None)
        if not upgrade:
            raise GameError("Unknown Breadworks upgrade.")
        if item in self.state["upgrades"]:
            raise GameError("This upgrade is already installed.")
        if self.state["coins"] < upgrade["cost"]:
            raise GameError(f"You need {upgrade['cost']} coins for this upgrade.")
        self.state["coins"] -= upgrade["cost"]
        self.state["upgrades"].append(item)
        return f"Installed {upgrade['title']}. Existing batches keep their remaining time."

    def query(self, name, args):
        arities = {"cargo": 1, "cargo_space": 0, "stored": 2, "free_space": 2,
                   "machine_status": 1, "get_tick": 0, "get_delivered": 0}
        if len(args) != arities[name]:
            raise GameError(f"{name}() expects {arities[name]} arguments.")
        if name == "cargo":
            self.check_item(args[0])
            return self.state["cargo"][args[0]]
        if name == "get_tick":
            return self.state["tick"]
        if name == "get_delivered":
            return self.state["stats"]["bread_delivered"]
        return {"cargo_space": self.cargo_space, "stored": self.stored,
                "free_space": self.free_space, "machine_status": self.machine_status}[name](*args)
