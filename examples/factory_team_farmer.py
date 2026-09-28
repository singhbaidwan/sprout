# DRONE 1 · FARMER · use Drone team mode
# Load the team starter to pair this with the courier program.
def go(x, y):
    if get_scenario() == "factory":
        navigate_to(x, y)
    else:
        while get_x() != x:
            if get_x() < x:
                move("east")
            else:
                move("west")
        while get_y() != y:
            if get_y() < y:
                move("south")
            else:
                move("north")

def maintain_supplies():
    x = get_x()
    y = get_y()
    if feature_enabled("irrigation") and get_supply("water") < 12:
        go(0, 0)
        refill_tank()
    if feature_enabled("fertilizer") and get_supply("fertilizer") == 0:
        if get_coins() >= 8:
            go(0, 0)
            buy_fertilizer(4)
    go(x, y)

def store_cargo():
    navigate_to("chest")
    for item in ["wheat", "flour", "bread"]:
        amount = min(cargo(item), free_space("chest", item))
        if amount > 0:
            unload(item, amount)

while True:
    for y in range(2):
        for x in range(6):
            navigate_to(x, y)
            maintain_supplies()
            if can_harvest():
                if cargo_space() < get_yield():
                    store_cargo()
                    navigate_to(x, y)
                if cargo_space() >= get_yield():
                    harvest()
            if feature_enabled("soil") and get_nutrients() <= 60:
                if get_supply("compost") > 0:
                    compost()
            if get_crop() == None:
                till()
                plant("wheat")
            if get_water() < 6:
                water()
            if feature_enabled("fertilizer") and not can_harvest():
                if not is_fertilized() and get_supply("fertilizer") > 0:
                    fertilize()
        store_cargo()
    wait()
