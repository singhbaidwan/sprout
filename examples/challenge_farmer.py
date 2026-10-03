# CHALLENGE FARMER · tend one row and supply the chest
# In Waterwise, the 60-unit tank starts full. Keep at least 36 units.
# Try fewer watering trips, sprinklers, or changing the planting area.
def store_grain():
    navigate_to("chest")
    amount = min(cargo("wheat"), free_space("chest", "wheat"))
    if amount > 0:
        unload("wheat", amount)

def tend_row():
    for x in range(6):
        navigate_to(x, 0)
        if can_harvest():
            if cargo_space() < get_yield():
                store_grain()
                navigate_to(x, 0)
            if cargo_space() >= get_yield():
                harvest()
        if get_crop() == None:
            till()
            plant("wheat")
        if not can_harvest() and get_water() < 6:
            if not feature_enabled("irrigation") or get_supply("water") >= 38:
                water()
    store_grain()
    wait()

while True:
    tend_row()
