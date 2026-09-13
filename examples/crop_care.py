# SMART CROP CARE · works in either chapter
# Choose your optional systems in Growing options first.
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

def tend_row():
    for x in range(6):
        go(x, 0)
        maintain_supplies()
        if can_harvest():
            if get_scenario() == "factory":
                if cargo_space() < get_yield():
                    navigate_to("chest")
                    amount = min(cargo("wheat"), free_space("chest", "wheat"))
                    if amount > 0:
                        unload("wheat", amount)
                    go(x, 0)
                if cargo_space() < get_yield():
                    print("Process chest stock before harvesting more.")
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
    print("Row tended. Rerun to harvest and feed the next crop.")

tend_row()
