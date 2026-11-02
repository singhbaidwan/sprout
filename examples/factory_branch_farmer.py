# BALANCED BAKERY · Continuous, all four routes built and enabled.
# Named belts deliver bread while the drone tends crops and optional recycling.
def return_products():
    if cargo("compost") > 0 or cargo("fertilizer") > 0:
        navigate_to("well")
        for item in ["compost", "fertilizer"]:
            amount = min(cargo(item), free_space("well", item))
            if amount > 0:
                unload(item, amount)

def recycling_cycle():
    if not feature_enabled("recycling"):
        return
    return_products()
    # Clear finished fertilizer before feeding the mixer.
    navigate_to("mixer")
    amount = min(stored("mixer", "fertilizer"), cargo_space(),
                 free_space("well", "fertilizer") - cargo("fertilizer"))
    if amount > 0:
        load("fertilizer", amount)
    return_products()

    navigate_to("composter")
    amount = min(stored("composter", "compost"), cargo_space())
    if amount > 0:
        load("compost", amount)
    # Reserve compost for soil; remaining output can feed the crop loop.
    if feature_enabled("fertilizer") and get_supply("fertilizer") < 24:
        reserve = max(0, 4 - get_supply("compost"))
        amount = max(0, cargo("compost") - reserve)
        if amount > 0:
            navigate_to("mixer")
            amount = min(amount, cargo("compost"), free_space("mixer", "compost"))
            if amount > 0:
                unload("compost", amount)
    return_products()

    # Collect residue from the well, not directly into harvest cargo.
    navigate_to("well")
    amount = min(stored("well", "residue"), cargo_space(),
                 free_space("composter", "residue") - cargo("residue"))
    if amount > 0:
        load("residue", amount)
    if cargo("residue") > 0:
        navigate_to("composter")
        amount = min(cargo("residue"), free_space("composter", "residue"))
        if amount > 0:
            unload("residue", amount)
    wait()

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
    go(x, y)

def tend_row():
    for x in range(6):
        go(x, 0)
        maintain_supplies()
        if can_harvest():
            if feature_enabled("recycling") and free_space("well", "residue") == 0:
                return
            if get_scenario() == "factory":
                if cargo_space() < get_yield():
                    navigate_to("chest")
                    amount = min(cargo("wheat"), free_space("chest", "wheat"))
                    if amount > 0:
                        unload("wheat", amount)
                    go(x, 0)
                if cargo_space() < get_yield():
                    return
            harvest()
        if feature_enabled("soil") and get_nutrients() <= 60:
            if get_supply("compost") > 0:
                compost()
        if get_crop() == None:
            till()
            plant("wheat")
        if feature_enabled("irrigation") and x in [1, 4]:
            if not has_sprinkler() and get_coins() >= 8:
                install_sprinkler()
        if get_water() < 6:
            water()
        if feature_enabled("fertilizer") and not can_harvest():
            if not is_fertilized() and get_supply("fertilizer") > 0:
                fertilize()

def store_grain():
    navigate_to("chest")
    amount = min(cargo("wheat"), free_space("chest", "wheat"))
    if amount > 0:
        unload("wheat", amount)

def automate():
    for line in ["grain", "flour", "bread", "bread_store"]:
        if conveyor_status(line) == "not_installed" or conveyor_status(line) == "paused":
            print("Build and enable all four bakery routes first.")
            return
    set_bread_routing("balanced")
    set_conveyor_policy("grain", 4, 6)
    set_conveyor_policy("flour", 0, 3)
    set_conveyor_policy("bread", 0, None)
    set_conveyor_policy("bread_store", 0, 4)
    for line in ["grain", "flour", "bread", "bread_store"]:
        set_conveyor_feed(line, True)
    # Balance bread until the chest holds four loaves; sell further output.
    while True:
        recycling_cycle()
        tend_row()
        store_grain()
        recycling_cycle()

automate()
