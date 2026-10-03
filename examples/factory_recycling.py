# FIRST RECYCLED FERTILIZER · enable Recycling in Breadworks first
# This finite demo makes both soil compost and crop fertilizer.
def store_wheat():
    navigate_to("chest")
    amount = min(cargo("wheat"), free_space("chest", "wheat"))
    if amount > 0:
        unload("wheat", amount)

def first_batch():
    if not feature_enabled("recycling"):
        print("Enable Recycling in the production panel, then run this example.")
        return
    for x in range(2):
        navigate_to(x, 0)
        if get_crop() == None:
            till()
            plant("wheat")
        if not can_harvest():
            if feature_enabled("irrigation") and get_supply("water") < 2:
                navigate_to("well")
                refill_tank()
                navigate_to(x, 0)
            water()
            while not can_harvest():
                wait()
        if cargo_space() < get_yield():
            store_wheat()
            navigate_to(x, 0)
        if cargo_space() < get_yield():
            print("Chest full. Process wheat with Farm to bakery first.")
            return
        if free_space("well", "residue") == 0:
            print("Residue hopper full. Run Recycling autopilot to clear it.")
            return
        harvest()
    store_wheat()
    navigate_to("well")
    amount = min(2, stored("well", "residue"), cargo_space(), free_space("composter", "residue"))
    if amount < 2:
        print("Free two cargo and composter input slots before this demo.")
        return
    load("residue", 2)
    navigate_to("composter")
    unload("residue", 2)
    while stored("composter", "compost") < 2:
        wait()
    load("compost", 2)
    navigate_to("mixer")
    if free_space("mixer", "compost") == 0:
        print("Mixer input full. Clear its fertilizer output first.")
        return
    unload("compost", 1)
    while stored("mixer", "fertilizer") < 2:
        wait()
    if cargo_space() < 2 or free_space("well", "compost") < 1 or free_space("well", "fertilizer") < 2:
        print("Free cargo or shed space, then return these products to the well.")
        return
    load("fertilizer", 2)
    navigate_to("well")
    unload("compost", 1)
    unload("fertilizer", 2)
    print("Returned 1 compost and 2 fertilizer. Enable Soil health or Fertilizer to use them.")

first_batch()
