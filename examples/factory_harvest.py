# HARVEST & STORE · all 24 growing plots
# Buildings occupy the rest of this 8 x 8 map.
def store_cargo():
    navigate_to("chest")
    for item in ["wheat", "flour", "bread"]:
        amount = min(cargo(item), free_space("chest", item))
        if amount > 0:
            unload(item, amount)
    return cargo_space() >= 3

def tend_field():
    for y in range(4):
        for x in range(6):
            navigate_to(x, y)
            if can_harvest():
                if cargo_space() < 3:
                    if not store_cargo():
                        print("Chest full. Run Farm to bakery to process stock.")
                        return
                    navigate_to(x, y)
                harvest()
            if get_crop() == None:
                till()
                plant("wheat")
            water()
    store_cargo()
    print("Field tended. Run again when more wheat is ripe.")

tend_field()
