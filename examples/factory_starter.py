# FIRST BREAD · turn 8 wheat into 4 loaves
# A new Breadworks chest holds 12 wheat.
if stored("chest", "wheat") >= 8 and cargo_space() >= 8:
    navigate_to("chest")
    load("wheat", 8)
    navigate_to("mill")
    unload("wheat", 8)

    while stored("mill", "flour") < 4:
        wait()
    load("flour", 4)

    navigate_to("oven")
    unload("flour", 4)
    while stored("oven", "bread") < 4:
        wait()
    load("bread", 4)

    navigate_to("depot")
    unload("bread", 4)
    print("First delivery! Try Harvest & store next.")
else:
    print("Need 8 chest wheat and 8 free cargo slots.")
    print("Try Harvest & store or Farm to bakery.")
