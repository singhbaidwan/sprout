# CONVEYOR DELIVERY · build all three routes and enable conveyors first.
def conveyor_demo():
    for line in ["grain", "flour", "bread"]:
        if conveyor_status(line) == "not_installed" or conveyor_status(line) == "paused":
            print("Build grain, flour and bread routes; enable conveyors in the workshop.")
            return
    if stored("chest", "wheat") < 8:
        print("Store at least 8 wheat in the chest first.")
        return
    started = get_tick()
    target = get_delivered() + 4
    for line in ["grain", "flour", "bread"]:
        set_conveyor_feed(line, True)
    for tick in range(200):
        if get_delivered() >= target:
            print("Conveyors delivered 4 loaves in", get_tick() - started, "ticks.")
            return
        wait()
    print("Inspect blocked routes and machine buffers; the demo stopped after 200 waits.")

conveyor_demo()
