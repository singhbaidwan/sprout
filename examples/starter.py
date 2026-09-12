# A little code. Your first harvest.
# The drone begins at (0, 0).

for plot in range(get_size()):
    if can_harvest():
        harvest()

    if get_crop() == None:
        till()
        plant("wheat")

    water()
    move("east")

print("First row done. Keep growing!")
