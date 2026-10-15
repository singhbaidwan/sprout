# STOCK TARGET DEMO · build/enable all bakery conveyors first.
def stock_demo():
    for line in ["grain", "flour", "bread"]:
        if conveyor_status(line) == "not_installed" or conveyor_status(line) == "paused":
            print("Build and enable all three bakery conveyors first.")
            return
    if stored("chest", "wheat") < 12:
        print("Store 12 wheat: eight to process and four to reserve.")
        return
    started = get_tick()
    goal = get_delivered() + 4
    set_conveyor_policy("grain", 4, 6)
    set_conveyor_policy("flour", 0, 3)
    set_conveyor_policy("bread", 0, None)
    for line in ["grain", "flour", "bread"]:
        set_conveyor_feed(line, True)
    for tick in range(240):
        if get_delivered() >= goal:
            print("Delivered four loaves in", get_tick() - started, "ticks.")
            print("Chest reserve:", stored("chest", "wheat"))
            return
        wait()
    print("Inspect buffers, queues and policy targets; demo limit reached.")

stock_demo()
