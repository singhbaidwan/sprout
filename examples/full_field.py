# Start in the northwest corner.
while get_x() != 0:
    move("west")
while get_y() != 0:
    move("north")

# The field wraps at every edge.
for row in range(get_size()):
    for column in range(get_size()):
        if can_harvest():
            harvest()
        if get_crop() == None:
            till()
            plant("wheat")
        water()
        move("east")
    move("south")

print("The whole field is planted!")
