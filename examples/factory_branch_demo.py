# BREAD BRANCH DEMO · build all four routes; start with empty bakery/queues.
def branch_demo():
    for line in ["grain", "flour", "bread", "bread_store"]:
        if conveyor_status(line) == "not_installed" or conveyor_status(line) == "paused":
            print("Build and enable bakery plus Bread storage routes first.")
            return
        if conveyor_items(line) > 0:
            print("Drain old queues before this fresh-stock demo.")
            return
    if stored("chest", "wheat") < 12 or stored("chest", "bread") > 0 or free_space("chest", "bread") < 4:
        print("Need 12 chest wheat, no chest bread and four free chest slots.")
        return
    if stored("mill", "wheat") > 0 or stored("mill", "flour") > 0 or machine_status("mill") == "working":
        print("Finish and empty the mill before testing.")
        return
    if stored("oven", "flour") > 0 or stored("oven", "bread") > 0 or machine_status("oven") == "working":
        print("Finish and empty the oven before testing.")
        return
    started = get_tick()
    sold = get_delivered()
    set_bread_routing("store")
    set_conveyor_policy("grain", 0, 6)
    set_conveyor_policy("flour", 0, 3)
    set_conveyor_policy("bread", 0, None)
    set_conveyor_policy("bread_store", 0, 4)
    for line in ["grain", "flour", "bread", "bread_store"]:
        set_conveyor_feed(line, True)
    for tick in range(160):
        if stored("chest", "bread") >= 4:
            break
        wait()
    set_bread_routing("sell")
    for tick in range(160):
        if stored("chest", "bread") >= 4 and get_delivered() - sold >= 2:
            print("Stored four bread and sold two in", get_tick() - started, "ticks.")
            return
        wait()
    print("Inspect chest capacity, route queues and feed policies.")

branch_demo()
