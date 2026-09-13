# ORDER RUNNER · process stock while transporting products
# Stock at least 24 wheat first; upgrades improve throughput.
# Start a timed order in the panel before running this program.
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

for cycle in range(7):
    production_cycle()
print("Delivered:", get_delivered(), "at tick", get_tick())
print("Try fewer trips, larger batches, and faster machines.")
