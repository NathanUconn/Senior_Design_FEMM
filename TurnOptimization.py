import numpy as np
from matplotlib import pyplot as plt
turns = 100
v_0 = 160
coil_radius = 1.5  # coil radius in inches
coil_circumference = 2*np.pi*coil_radius
r_per_in = 6.385/(1000*12)  # the resistance per inch of cable
turns_arr = []
resistance_arr = []
current_arr = []
force_arr = []

while turns < 600000:
    coil_wire_length = turns * coil_circumference
    r_coil = r_per_in * coil_wire_length
    resistance = 4.7 + r_coil
    current = v_0/resistance
    force = (current*turns)**2

    turns_arr.append(turns)
    resistance_arr.append(resistance)
    current_arr.append(current)
    force_arr.append(force)
    turns+=50

figure, ax = plt.subplots()

plt.title("Force Versus Turns")
plt.xlabel("Turns")
plt.ylabel("Force")
plt.plot(turns_arr, force_arr)
plt.show()
