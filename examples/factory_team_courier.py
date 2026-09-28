# DRONE 2 · COURIER · use Drone team mode
# This drone processes grain while Drone 1 grows it.
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

while True:
    production_cycle()
