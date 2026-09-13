# FARM TO BAKERY · a repeatable farm + production routine
# Keep products moving while the other machine works.
def ship_bread():
    if cargo("bread") > 0:
        navigate_to("depot")
        unload("bread", cargo("bread"))

def production_cycle():
    ship_bread()
    # First free the oven's output buffer.
    navigate_to("oven")
    amount = min(stored("oven", "bread"), cargo_space())
    if amount > 0:
        load("bread", amount)
        ship_bread()

    # Move finished flour forward; carry-over cargo is reused.
    navigate_to("mill")
    amount = min(stored("mill", "flour"), cargo_space(),
                 free_space("oven", "flour") - cargo("flour"))
    if amount > 0:
        load("flour", amount)
    if cargo("flour") > 0:
        navigate_to("oven")
        amount = min(cargo("flour"), free_space("oven", "flour"))
        if amount > 0:
            unload("flour", amount)

    # A new batch is milled during the next round of travel.
    navigate_to("chest")
    amount = min(stored("chest", "wheat"), cargo_space(),
                 free_space("mill", "wheat") - cargo("wheat"), 8)
    if amount > 0:
        load("wheat", amount)
    if cargo("wheat") > 0:
        navigate_to("mill")
        amount = min(cargo("wheat"), free_space("mill", "wheat"))
        if amount > 0:
            unload("wheat", amount)
    wait()

# Refill from six plots; keeping each run small leaves time to bake.
def tend_row():
    for x in range(6):
        navigate_to(x, 0)
        if can_harvest():
            if cargo_space() < 3:
                navigate_to("chest")
                amount = min(cargo("wheat"), free_space("chest", "wheat"))
                if amount > 0:
                    unload("wheat", amount)
                navigate_to(x, 0)
            if cargo_space() >= 3:
                harvest()
        if get_crop() == None:
            till()
            plant("wheat")
        water()
    navigate_to("chest")
    amount = min(cargo("wheat"), free_space("chest", "wheat"))
    if amount > 0:
        unload("wheat", amount)

tend_row()
for cycle in range(5):
    production_cycle()
print("Bread delivered so far:", get_delivered())
print("Run again to keep this little factory growing.")
