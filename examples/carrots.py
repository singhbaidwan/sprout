# Unlock carrots in Room to grow first.
# One harvest pays for the next seed.
for plot in range(6):
    if get_crop() != None:
        water()
        while not can_harvest():
            wait()
        harvest()

    till()
    plant("carrot")
    water()

    while not can_harvest():
        wait()
    harvest()
    move("east")

print("Six carrots, freshly harvested.")
