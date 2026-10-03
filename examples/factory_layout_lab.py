# LAYOUT DELIVERY TEST · the same four-loaf job on any workshop layout.
# Start with empty mill/oven buffers, eight chest wheat, and eight free cargo slots.
def delivery_test():
    if stored("chest", "wheat") < 8 or cargo_space() < 8:
        print("Need 8 wheat in the chest and 8 free cargo slots.")
        return
    if stored("mill", "wheat") > 0 or stored("mill", "flour") > 0 or machine_status("mill") == "working":
        print("Empty the mill and finish its batch before testing.")
        return
    if stored("oven", "flour") > 0 or stored("oven", "bread") > 0 or machine_status("oven") == "working":
        print("Empty the oven and finish its batch before testing.")
        return
    started = get_tick()
    delivered = get_delivered()
    navigate_to("chest")
    load("wheat", 8)
    navigate_to("mill")
    unload("wheat", 8)
    # Feed each flour as soon as it is ready; milling and baking overlap.
    for loaf in range(4):
        navigate_to("mill")
        while stored("mill", "flour") < 1:
            wait()
        load("flour", 1)
        navigate_to("oven")
        unload("flour", 1)
    while stored("oven", "bread") < 4:
        wait()
    load("bread", 4)
    navigate_to("depot")
    unload("bread", 4)
    print("Layout test:", get_delivered() - delivered, "loaves in", get_tick() - started, "ticks.")

delivery_test()
