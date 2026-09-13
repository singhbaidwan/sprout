# SPRINKLER NETWORK · enable Irrigation in Growing options
# One sprinkler covers a 3 x 3 square and costs 8 coins.
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

if feature_enabled("irrigation"):
    width = get_size()
    rows = range(1, get_size(), 3)
    if get_scenario() == "factory":
        width = 6
        rows = [1, 3]
    for y in rows:
        for x in range(1, width, 3):
            go(x, y)
            if not has_sprinkler() and get_coins() >= 8:
                install_sprinkler()
    go(0, 0)
    refill_tank()
    set_irrigation(True)
    for tick in range(36):
        if get_supply("water") < 8:
            refill_tank()
        wait()
    print("Tank remaining:", get_supply("water"))
    print("Sprinklers also run while your drone farms or delivers.")
else:
    print("Enable Irrigation in Growing options, then run again.")
