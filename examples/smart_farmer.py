# A reusable routine for every plot.
def tend_plot():
    if can_harvest():
        harvest()
    if get_crop() == None:
        till()
        plant("wheat")
    water()

# Run again for another harvest cycle.
for row in range(get_size()):
    for column in range(get_size()):
        tend_plot()
        move("east")
    move("south")

print("Harvest cycle done.")
print("Coins:", get_coins())
