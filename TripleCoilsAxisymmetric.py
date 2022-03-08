import femm
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.animation import FuncAnimation
import numpy as np
import os
from datetime import datetime
import json
import csv
import time as time_module

start_time = time_module.time()

voltage_test = False
num_turns_test = False
starting_pos_test = False
coil_2_threshold_test = False
coil_3_threshold_test = False
model_type = "actual"  # spaced, condensed, condensed with spacer
display_plots = True

# Circuit Parameters #
if voltage_test:
    voltage_arr = [140, 160, 225, 350]
else:
    voltage_arr = [160]

if num_turns_test:
    num_turns_arr = [100, 200, 300, 315]
else:
    num_turns_arr = ["actual"]  # change to ["actual"] if want 500, 500, 420

# Coil Timing Arrays #
if starting_pos_test:  # location of the tip of the projectile relative to the start of coil 1
    starting_pos_arr = [-0.325, -0.25, 0, 0.25, 0.325]
else:
    starting_pos_arr = [.315]

if coil_2_threshold_test:
    coil_2_thresh_arr = np.ndarray.tolist(np.linspace(1.0, 1.5, 8))
else:
    coil_2_thresh_arr = [1.285714286]  # 1.625

if coil_3_threshold_test:
    coil_3_thresh_arr = np.ndarray.tolist(np.linspace(1.0, 1.5, 8))
else:
    coil_3_thresh_arr = [1.357142857]  # 1.4

delta_t = 0.0025  # time step in seconds
decimals = (str(delta_t)[::-1].find('.'))

max_time = 1.5

# Firing Mode: Only one can be true #
sequential_cutoff = False
sequential_firing = True

if num_turns_arr == ["actual"] and sequential_cutoff:
    print("WARNING: Sequential Cuttoff Not Validated for Actual Number of Turns(500, 500, 420)")
    print("Please retry with constant turn numbers")
    quit()

# Drag Parameters #

body_loaded = True   # Whether the cylindrical body is loaded into the sled or if the system is being dry fired (
water = True
if water:
    fluid_density = 1000  # kg/m^3, water
else:
    fluid_density = 1.225 # kg/m^#, air
proj_cross_sec = 4.90874 * (0.0254**2)  # area of tube opening in m^2
drag_coeff = 0.75  # drag coefficient of the body, GET FROM JASON

# Friction Parameters #

mu = 0.05  # coefficient of dynamic friction, 0.5 for sliding PLA on steel, very low for rolling
mu_s = 1.0  # coefficient of static friction, 1.0 for sliding PLA on steel, N/A for rolling


header = ["Model Type", "Voltage", "Turns", "Starting Distance of Tip From Coil 1", "Coil 2 Distance Threshold", "Coil 3 Distance Threshold", "Max Velocity", "Exit Velocity"]

output_arr_master = []  # array for storing the output data for the batchrun.csv file

print("Voltage Array:", voltage_arr)
print("Num Turns Array:", num_turns_arr)
print("Starting Position Array", starting_pos_arr)
print("Coil 2 Threshold Array", coil_2_thresh_arr)
print("Coil 3 Threshold Array", coil_3_thresh_arr)

num_combos = len(voltage_arr) * len(num_turns_arr) * len(starting_pos_arr) * len(coil_2_thresh_arr) * len(coil_3_thresh_arr)
print("Number of testing combos:", num_combos)

# Main testing loops #
for volt in voltage_arr:
    for num_turns in num_turns_arr:
        for starting_pos in starting_pos_arr:
            for coil_2_threshold_dist in coil_2_thresh_arr:
                for coil_3_threshold_dist in coil_3_thresh_arr:

                    if num_turns == "actual":  # 500, 500, 420
                        coil_1_turns, coil_2_turns, coil_3_turns = 500, 500, 420
                    else:
                        coil_1_turns, coil_2_turns, coil_3_turns = num_turns, num_turns, num_turns

                    if water:
                        test_type = "Submerged"
                    else:
                        test_type = "Dry"
                    print("\nModel Type", model_type, "Test Type", test_type, "Voltage", volt, "Number of Turns", num_turns, "Starting Distance From Tip to Coil 1:", starting_pos, "Coil 2 Threshold Dist:", coil_2_threshold_dist, "Coil 3 Threshold Dist:", coil_3_threshold_dist)

                    current_directory = os.getcwd()  # get current working directory for file creation

                    femm.openfemm()

                    # Model Information - could move outside #
                    if model_type == "condensed":
                        model = "ThreeCoilModelAxi.fem"
                    elif model_type == "spaced":
                        model = "ThreeCoilModelAxi_Spaced.fem"
                    elif model_type == "actual":
                        model = "ThreeCoilModelAxi_actual.fem"
                    else:
                        model = ""
                        print("Improper model_type. Must be either actual, condensed, or spaced")
                        quit()
                    model_path = "Models/" + model
                    femm.opendocument(model_path)
                    temp_path = "Models/" + "temp.fem"
                    femm.mi_saveas(temp_path)
                    femm.mi_seteditmode("group")

                    # Array Creation for keeping track of data #
                    pos = []
                    coil_force = []
                    drag_force = []
                    vel = []

                    # Create test data folder #
                    path = "Test Data"
                    final_directory = os.path.join(current_directory, path)
                    if not os.path.exists(final_directory):
                        os.makedirs(final_directory)

                    test_folder_path = "Test Data/" + str(volt) + "Volts-" + str(num_turns) + "Turns-"+model_type+"-"+ str(round(starting_pos, 3)) + "in-" + str(round(coil_2_threshold_dist, 3)) + "in-" + str(round(coil_3_threshold_dist, 3)) + "in-" + str(datetime.now().strftime("%B-%d-%Y-%H-%M-%S"))
                    final_directory = os.path.join(current_directory, test_folder_path)
                    if not os.path.exists(final_directory):
                        os.makedirs(final_directory)

                    # Projectile Parameters: ALL REFER TO THE SLUG EXCEPT FOR MASS WHERE IT IS A COMBINATION OF SLUG, SLED, AND BODY !!!CHANGE!!!
                    proj_r = 0.357  # radius of projectile in inches
                    proj_l = 1.3  # length of projectile in inches
                    proj_vol = np.pi * (proj_r**2) * proj_l  # volume of projectile in in^3
                    proj_vol = proj_vol * 1.63871e-5  # volume of projectile in m^3
                    proj_density = 70860  # density of iron in kg/m^3
                    slug_mass = proj_density * proj_vol
                    sled_mass = 58.21/1000
                    body_mass = 105.42/1000
                    water_mass = 643.5/1000  # calculated using 8 inches of water in the tube for expulsion

                    if body_loaded:  # if the cylindrical body is in the sled or just dry launching the sled
                        proj_mass = slug_mass + sled_mass + body_mass
                    else:
                        proj_mass = slug_mass + sled_mass
                    if water:
                        proj_mass += water_mass

                    # Coil Parameters
                    coil_radius = 1.7345  # coil radius in inches
                    coil_circumference = 2*np.pi*coil_radius
                    r_per_in = 6.385/(1000*12)  # the resistance per inch of cable
                    # Now Taken Care of in Coil Class #
                    # coil_wire_length = num_turns * coil_circumference
                    # r_coil = r_per_in * coil_wire_length
                    # print("R coil", r_coil)

                    # print("Slug Mass", slug_mass, "kg")
                    # print("Projectile Mass:", proj_mass, "kg")

                    # Electrical parameters - could move outside loop
                    voltage_0 = volt  # initial voltage in volts
                    r_resistor = 4.7  # resistance of discharge resistors
                    # r = r_resistor + r_coil  # resistance of circuit in Ohms, from the resistor and the resistance of the coil
                    # print("Total resistance:", r, "Ohms")
                    # I_0 = voltage_0/r  # initial current in Amps
                    c = 30/1000  # capacitance of each capacitor (default is 30000uF, 30mF, or 0.03F)

                    if model_type == "condensed":
                        coil_1_start_location = 1.5
                        simulation_file_proj_center_start_y = 1.5
                    elif model_type == "spaced":
                        coil_1_start_location = -1.5
                        simulation_file_proj_center_start_y = -1.5
                    elif model_type == "actual":
                        coil_1_start_location = 1
                        simulation_file_proj_center_start_y = 1
                    else:
                        simulation_file_proj_center_start_y = 0
                        coil_1_start_location = 0
                        print("Improper model_type. Must be either actual, condensed, or spaced")
                        quit()
                    simulation_file_proj_tip_start_y = simulation_file_proj_center_start_y + proj_l/2

                    change_in_proj_tip_start_y = starting_pos - simulation_file_proj_tip_start_y + coil_1_start_location

                    if change_in_proj_tip_start_y != 0:
                        print("Moving tip of projectile", starting_pos, "inches from the start of coil 1 a change of", round(change_in_proj_tip_start_y, decimals), "inches")

                    femm.mi_seteditmode('group')
                    femm.mi_selectgroup(1)
                    femm.mi_movetranslate(0, change_in_proj_tip_start_y)

                    # proj_center_start_y = 1.5
                    proj_center_start_y = starting_pos-proj_l/2+coil_1_start_location
                    proj_center_end_y = 13.5
                    v = 0  # initial velocity in in/sec

                    proj_curr_y = proj_center_start_y
                    # print("Current y:", proj_curr_y)
                    time = []
                    current_arr = []
                    latest_time = 0
                    time_since_coil_activation = 0

                    config_dict = {'Model': model, "Test Type": test_type, "Voltage": volt, "Num Turns": num_turns, "Starting Position": proj_center_start_y,"Coil 2 Threshold Distance": coil_2_threshold_dist, "Coil 3 Threshold Distance": coil_3_threshold_dist, 'Slug Radius': proj_r, 'Slug Length':  proj_l, 'Projectile Volume': proj_vol, 'Slug Mass': slug_mass, 'Projectile Mass': proj_mass, 'Proj Center Start':  proj_center_start_y, 'Max Time': max_time, "Delta-T": delta_t}

                    json_output = json.dumps(config_dict)
                    config_path = test_folder_path + "/config_dict.json"
                    f = open(config_path, "w")
                    f.write(json_output)
                    f.close()

                    # 5, 7.5 for Air
                    # 1.5, 2.5 for Coil 1 - Group 2, Coil Center at y = 2.5 (r_center,z_center)
                    # 1.5, 5.5 for Coil 2 - Group 3, Coil Center at y = 5
                    # 1.5, 7.5 for Coil 3 - Group 4, Coil Center at y = 7.5


                    class Coil:
                        def __init__(self, num, x_center, y_center, turns, group, on, shut_down_time, power_on_time):
                            self.num = num
                            self.x_center = x_center
                            self.y_center = y_center
                            self.turns = turns
                            self.resistance = r_per_in * turns * coil_circumference
                            self.init_curr = voltage_0/(self.resistance+r_resistor)
                            self.group = group
                            self.on = on
                            self.shut_down_time = shut_down_time
                            self.power_on_time = power_on_time


                    if model_type == "condensed":
                        coil_1 = Coil(1, 1.7345, 2.5, coil_1_turns, 2, True, 0, 0)
                        coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1)
                        coil_3 = Coil(3, 1.7345, 7.5, coil_3_turns, 4, True, 0, -1)
                    elif model_type == "spaced":
                        coil_1 = Coil(1, 1.7345, -0.5, coil_1_turns, 2, True, 0, 0)
                        coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1)
                        coil_3 = Coil(3, 1.7345, 10.5, coil_3_turns, 4, True, 0, -1)
                    # elif model_type == "actual":
                    #     coil_1 = Coil(1, 1.7345, 2.5, coil_1_turns, 2, True, 0, 0)
                    #     coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1)
                    #     coil_3 = Coil(3, 1.7345, 7.875, coil_3_turns, 4, True, 0, -1)
                    elif model_type == "actual":
                        coil_1 = Coil(1, 1.7345, 2, coil_1_turns, 2, True, 0, 0)
                        coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1)
                        coil_3 = Coil(3, 1.7345, 8, coil_3_turns, 4, True, 0, -1)
                    else:
                        coil_1, coil_2, coil_3 = [], [], []
                        print("Improper model_type. Must be either actual, condensed, or spaced")
                        quit()

                    coils = [coil_1, coil_2, coil_3]

                    def coil_initialization():
                        for coil in coils:
                            femm.mi_selectlabel(coil.x_center, coil.y_center)
                            femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group, coil.turns)  # positive loop for right
                            coil.on = True
                            femm.mi_clearselected()

                    coil_initialization()


                    def sequential_firing_check():  # function to turn on and cut off coils in sequence, only coil 1 starts on
                        global time_since_coil_activation
                        femm.mi_seteditmode('blocks')
                        current_coil = 0

                        for coil in coils:
                            if coil.power_on_time != -1:
                                current_coil = coil.num

                        for coil in coils:
                            # print("Coil", coil.num, "Leading edge at", coil.y_center, "Projectile edge at", proj_curr_y+0.65)
                            if coil.num == current_coil:  # if the coil is the current coil, check to see if it is past the midpoint
                                if proj_curr_y >= coil.y_center and coil.on:
                                    femm.mi_selectlabel(coil.x_center, coil.y_center)
                                    femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                                    coil.shut_down_time = time[-1]
                                    # print("Coil", str(coil.num), "turned off")
                                    coil.on = False
                                    current_coil += 1
                                elif proj_curr_y < coil.y_center and not coil.on:
                                    coil.power_on_time = 0  # used to ensure the coil is kept as the current coil
                                    if coil.num == 2:
                                        coil_threshold_dist = coil_2_threshold_dist
                                    else:
                                        coil_threshold_dist = coil_3_threshold_dist
                                    if proj_curr_y+proj_l/2 >= coil.y_center-coil_threshold_dist:
                                        femm.mi_selectlabel(coil.x_center, coil.y_center)
                                        femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group, coil.turns)  # negative loop for left, positive loop for right
                                        femm.mi_clearselected()
                                        coil.power_on_time = time[-1]
                                        # print("Coil", str(coil.num), "turned on")
                                        coil.on = True
                                        time_since_coil_activation = 0
                            elif coil.num != current_coil and coil.on:  # used for the initial proper setting
                                femm.mi_selectlabel(coil.x_center, coil.y_center)
                                femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                                # print("Coil", str(coil.num), "turned off")
                                coil.on = False
                            femm.mi_clearselected()
                        femm.mi_clearselected()


                    def sequential_cutoff_check():  # function to turn off coils in sequence, all start on
                        femm.mi_seteditmode('blocks')
                        for coil in coils:
                            if proj_curr_y >= coil.y_center and coil.on:
                                femm.mi_selectlabel(coil.x_center, coil.y_center)
                                femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                                femm.mi_clearselected()
                                coil.shut_down_time = time[-1]
                                print("Coil", str(coil.num), "turned off")
                                coil.on = False
                            elif proj_curr_y < coil.y_center and not coil.on:
                                femm.mi_selectlabel(coil.x_center, coil.y_center)
                                femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group, coil.turns)  # negative loop for left, positive loop for right
                                print("Coil", str(coil.num), "turned on")
                                coil.on = True
                            femm.mi_clearselected()

                    # Main Loop #

                    while proj_curr_y < proj_center_end_y and latest_time < max_time:

                        # Check to see if any of the coils should be turned off/on
                        if sequential_firing:
                            sequential_firing_check()

                        elif sequential_cutoff:
                            sequential_cutoff_check()

                        any_coils_on = False
                        r = 99999999999999999999999999
                        for coil in coils:
                            if coil.on:
                                any_coils_on = True
                                r = coil.resistance + r_resistor


                        voltage = voltage_0 * np.exp(-time_since_coil_activation/(r*c))  # voltage due to discharging capacitors
                        # print("Voltage:", voltage, "Volts")
                        current = round(voltage/r, decimals)  # current through coils
                        current_arr.append(current)
                        # print("Current:", current, "Amps")
                        femm.mi_modifycircprop("New Circuit", 1, current)  # propnum = 1 is the total current, change the current in FEMM

                        femm.mi_seteditmode('group')  # select groups of points/lines
                        if any_coils_on:
                            femm.mi_analyze()  # run the FEMM simulation
                            femm.mi_loadsolution()  # gather the FEMM simulation data

                            femm.mo_clearblock()
                            femm.mo_groupselectblock(1)  # select the slug (body 1)
                            force_y = femm.mo_blockintegral(19)  # get the force acting on the slug
                        else:
                            force_y = 0
                        # print("FEMM Reported Force on Slug", force_y)

                        pos.append(proj_curr_y)  # add the current position to the position array
                        if len(time) != 0:  # if not at the start of the simulation, determine the drag force
                            time.append(latest_time)
                            drag_force_y = 1/2*drag_coeff*fluid_density*((vel[-1]*0.0254)**2)*proj_cross_sec
                        else:  # drag force is 0 at time 0, breaks otherwise
                            time.append(0)
                            drag_force_y = 0
                        latest_time += delta_t  # increment the time step
                        latest_time = round(latest_time, decimals)  # round time to speed up code
                        time_since_coil_activation += delta_t  # modify the time since coil activation for keeping track of the current
                        # print("FORCE:", force_y)
                        coil_force.append(force_y)  # coil force array for plotting purposes

                        drag_force.append(drag_force_y)  # drag force array for plotting purposes
                        #print("Drag Force", drag_force_y, "N")

                        force_y += -drag_force_y  # CHANGE LATER SINCE THIS IS NOT THE CASE

                        # Calculate Dynamic Frictional Forces #
                        if round(v,2) == 0:
                            friction_force = 0
                        elif v > 0:
                            friction_force = - mu*proj_mass*9.81
                        else:  # v < 0
                            friction_force = mu*proj_mass*9.81

                        # print("Force y:", force_y, "Friction Force:", friction_force)
                        force_y += friction_force  # positive and negative are taken care of in the frictional force
                        # print("New force y:", force_y)

                        # Determine acceleration, delta-v, and delta-pos #
                        acc = force_y/proj_mass  # a=F/m
                        acc = 39.3701 * acc  # acceleration of the projectile in in/s^2
                        # print("Acceleration:", acc, "in/s^2")
                        delta_v = acc * delta_t  # dv=a*dt
                        # print("Delta-v:", delta_v, "in/s")
                        vel.append(v) # velocity array for plotting purposes

                        proj_curr_y += v*delta_t + 0.5*acc*delta_t*delta_t  # based on kinematic equation dX = v_0*t+1/2*a*t^2

                        v += delta_v  #
                        femm.mo_clearblock()
                        femm.mi_selectgroup(1)
                        femm.mi_movetranslate(0, v*delta_t + 0.5*acc*delta_t*delta_t)  # move the object in FEMM

                    femm.mi_close() # close postprocessor
                    femm.closefemm()  # close entire FEMM window

                    coil_force = np.array(coil_force)  # convert to numpy array for efficient data processing
                    pos = np.array(pos)

                    for coil in coils:  # get the pulse duration for each coil from its start and end time, report out
                        pulse_duration = round(coil.shut_down_time - coil.power_on_time, decimals)
                        if coil.num == 1:
                            print("Coil", coil.num, "pulse duration:", pulse_duration, "seconds from", coil.power_on_time, "to", coil.shut_down_time, "seconds")
                        else:
                            print("Coil", coil.num, "pulse duration:", pulse_duration, "seconds from", coil.power_on_time, "to", coil.shut_down_time, "seconds. A delay of", round(coil.power_on_time - coils[coil.num-2].shut_down_time, decimals), "seconds since last shutoff")

                    coil_1_pulse_duration = round(coil_1.shut_down_time - coil_1.power_on_time, decimals)
                    coil_2_pulse_duration = round(coil_2.shut_down_time - coil_2.power_on_time, decimals)
                    coil_3_pulse_duration = round(coil_3.shut_down_time - coil_3.power_on_time, decimals)
                    # exit velocity defined as when the slug center reaches 12.85 in the actual model
                    full_exit_index = 0
                    exit_time = 0
                    for x in pos:
                        if x > 12.85:
                            full_exit_index = (np.where(pos == x))[0][0]
                            exit_time = time[full_exit_index]
                            break
                    exit_velocity = vel[full_exit_index]
                    output_dict = {"Max Velocity (in/s)": max(vel), "Exit Velocity": exit_velocity, "Coil 1 Pulse Duration": coil_1_pulse_duration, "Coil 1 Pulse Start": coil_1.power_on_time, "Coil 1 Pulse Stop": coil_1.shut_down_time, "Coil 2 Pulse Duration": coil_2_pulse_duration, "Coil 2 Pulse Start": coil_2.power_on_time, "Coil 2 Pulse Stop": coil_2.shut_down_time, "Coil 3 Pulse Duration": coil_3_pulse_duration, "Coil 3 Pulse Start": coil_3.power_on_time, "Coil 3 Pulse Stop": coil_3.shut_down_time}

                    # JSON output #
                    json_output = json.dumps(output_dict)
                    output_path = test_folder_path + "/output.json"
                    f = open(output_path, "w")
                    f.write(json_output)
                    f.close()

                    anim_frames = min(len(time)-1, 100)  # number of frames for the animations

                    def animate_force_plot():  # does what it says on the tin
                        time_plt = []
                        coil_force_plt = []
                        drag_force_plt = []
                        curr_plt = []

                        figure, ax = plt.subplots()

                        ax2 = ax.twinx()

                        plt.title("Force(N) of Slug and Current Through Coils(A) Versus Time(s)")
                        plt.xlabel("Time(s)")
                        ax.set_ylabel("Force(N)", color="blue")

                        ax2.set_ylabel("Current(A)", color="red")

                        # Setting limits for x and y axis
                        ax.set_xlim(0, time[-1])
                        lower_bound = min(coil_force)
                        if lower_bound <= 0:
                            lower_bound = lower_bound * 1.1
                        else:
                            lower_bound = lower_bound / 1.1
                        ax.set_ylim(lower_bound, max(coil_force)*1.1)
                        ax2.set_ylim(0, max(current_arr)*1.1)

                        # Since plotting a single graph
                        coil_force_line, = ax.plot(0, 0, color="blue", label="Coil Force")
                        drag_force_line, = ax.plot(0, 0, color="purple", label="Drag Force")
                        curr_line, = ax2.plot(0, 0, color="red", label="Current")

                        # Plot Vertical lines for
                        for coil in coils:
                            label_string = "Coil " + str(coil.num)
                            if coil.num == 1:
                                line_color = "orange"
                            elif coil.num == 2:
                                line_color = "green"
                            else:
                                line_color = "black"
                            # ax.axvline(x=coil.shut_down_time, color=line_color, label=label_string)
                            # ax.axvline(x=coil.power_on_time, color=line_color)
                            ax.add_patch(Rectangle((coil.power_on_time, lower_bound), coil.shut_down_time-coil.power_on_time, max(coil_force)*1.1, color=line_color, alpha=0.5, label=label_string))

                        fig_path = test_folder_path + "/coil_force.png"

                        def animation_function(i):
                            i_orig = i
                            i = int(i * len(time)/anim_frames)
                            time_plt.append(time[i])
                            coil_force_plt.append(coil_force[i])
                            drag_force_plt.append(drag_force[i])
                            curr_plt.append(current_arr[i])

                            coil_force_line.set_xdata(time_plt)
                            coil_force_line.set_ydata(coil_force_plt)
                            drag_force_line.set_xdata(time_plt)
                            drag_force_line.set_ydata(drag_force_plt)
                            curr_line.set_xdata(time_plt)
                            curr_line.set_ydata(curr_plt)
                            if i_orig == anim_frames - 1:
                                plt.savefig(fig_path)
                            return coil_force_line, drag_force_line, curr_line,


                        animation = FuncAnimation(figure, func = animation_function, interval=50, frames=anim_frames, blit=False, repeat=False)
                        ax.legend(loc="upper right")
                        ax2.legend(loc="upper left")
                        if display_plots:
                            plt.show(block=False)
                            plt.pause(7)
                            plt.close()


                    def animate_pos_plot(): # does what it says on the tin
                        time_plt = []
                        pos_plt = []

                        figure, ax = plt.subplots()

                        plt.title("Pos(in) of Slug Versus Time(s)")
                        plt.xlabel("Time(s)")
                        plt.ylabel("Pos(in)")

                        lower_bound = min(pos)
                        if lower_bound <= 0:
                            lower_bound = lower_bound * 1.1
                        else:
                            lower_bound = lower_bound / 1.1

                        # Setting limits for x and y axis
                        ax.set_xlim(0, time[-1])
                        ax.set_ylim(lower_bound, max(pos)*1.1)

                        # Since plotting a single graph
                        line, = ax.plot(0, 0)

                        fig_path = test_folder_path + "/pos.png"

                        def animation_function(i):
                            i_orig = i
                            i = int(i * len(time)/anim_frames)
                            time_plt.append(time[i])
                            pos_plt.append(pos[i])

                            line.set_xdata(time_plt)
                            line.set_ydata(pos_plt)

                            if i_orig == anim_frames - 1:
                                plt.savefig(fig_path)
                            return line,


                        animation = FuncAnimation(figure, func = animation_function, interval=50, frames=anim_frames, blit=False, repeat=False)
                        if display_plots:
                            plt.show(block=False)
                            plt.pause(7)
                            plt.close()


                    def animate_vel_plot(): # does what it says on the tin
                        time_plt = []
                        vel_plt = []

                        figure, ax = plt.subplots()

                        lower_bound = min(vel)
                        if lower_bound <= 0:
                            lower_bound = lower_bound * 1.1
                        else:
                            lower_bound = lower_bound / 1.1

                        # Setting limits for x and y axis
                        ax.set_xlim(0, time[-1])
                        ax.set_ylim(lower_bound, max(vel)*1.1)

                        # Since plotting a single graph
                        line, = ax.plot(0, 0)

                        fig_path = test_folder_path + "/vel.png"
                        ax.axvline(x=exit_time, color="green", label="Expulsion")

                        def animation_function(i):
                            i_orig = i
                            i = int(i * len(time)/anim_frames)
                            time_plt.append(time[i])
                            vel_plt.append(vel[i])

                            line.set_xdata(time_plt)
                            line.set_ydata(vel_plt)
                            if i_orig == anim_frames - 1:
                                plt.savefig(fig_path)
                            return line,


                        animation = FuncAnimation(figure, func = animation_function, interval=50, frames=anim_frames, blit=False, repeat=False)
                        plt.title("Vel(in/s) of Slug Versus Time(s)")
                        plt.xlabel("Time(s)")
                        plt.ylabel("Vel(in/s)")
                        if display_plots:
                            plt.show(block=False)
                            plt.pause(7)
                            plt.close()


                    def animate_coil_plot():  # custom animation of projectile being launched
                        fig, ax = plt.subplots()
                        fig.set_dpi(100)
                        fig.set_size_inches(7, 6.5)
                        ax.set_facecolor("black")

                        time_text = ax.text(0.65,0.9, "Time Text", bbox={'facecolor':'black', 'alpha':0, 'pad':1}, transform=ax.transAxes, ha="left", color="white", fontsize=12)
                        velocity_text = ax.text(0.65,0.85, "Velocity Text", bbox={'facecolor':'black', 'alpha':0, 'pad':1}, transform=ax.transAxes, ha="left", color="white", fontsize=12)

                        lower_bound = min(pos)
                        if lower_bound <= 0:
                            lower_bound = lower_bound * 1.1 - proj_l
                        else:
                            lower_bound = lower_bound / 1.1 - proj_l

                        # Setting limits for x and y axis
                        ax.set_xlim(-10, 10)
                        ax.set_ylim(lower_bound, max(pos)*1.1+proj_l)
                        patch = plt.Rectangle((0-proj_r, 0), width=proj_r*2, height=proj_l, fc="grey")

                        c1p1 = plt.Rectangle((-1.625, 1.5), 0.39, 2, fc="green")
                        c1p2 = plt.Rectangle((1.235, 1.5), 0.39, 2, fc="green")

                        c2p1 = plt.Rectangle((-1.625, 4), 0.39, 2, fc="green")
                        c2p2 = plt.Rectangle((1.235, 4), 0.39, 2, fc="green")

                        c3p1 = plt.Rectangle((-1.625, 6.5), 0.39, 2, fc="green")
                        c3p2 = plt.Rectangle((1.235, 6.5), 0.39, 2, fc="green")


                        def init():
                            x, y = patch.get_x(), patch.get_y()
                            patch.set_x(x)
                            patch.set_y(y)
                            ax.add_patch(patch)

                            ax.add_patch(c1p1)
                            ax.add_patch(c1p2)
                            ax.add_patch(c2p1)
                            ax.add_patch(c2p2)
                            ax.add_patch(c3p1)
                            ax.add_patch(c3p2)

                            time_text.set_text("Frame 0")
                            velocity_text.set_text("Frame 0")
                            return patch, time_text, velocity_text, c1p1, c1p2, c2p1, c2p2, c3p1, c3p2

                        def animate(i):
                            x = patch.get_x()
                            y = pos[i]
                            patch.set_x(x)
                            patch.set_y(y-proj_l/2)

                            t = round(i * delta_t, decimals)
                            if sequential_cutoff:
                                if t == coil_1.shut_down_time:
                                    c1p1.set_facecolor("red")
                                    c1p2.set_facecolor("red")
                                elif t < coil_1.shut_down_time:
                                    c1p1.set_facecolor("green")
                                    c1p2.set_facecolor("green")
                                if t == coil_2.shut_down_time:
                                    c2p1.set_facecolor("red")
                                    c2p2.set_facecolor("red")
                                elif t < coil_2.shut_down_time:
                                    c2p1.set_facecolor("green")
                                    c2p2.set_facecolor("green")
                                if t == coil_3.shut_down_time:
                                    c3p1.set_facecolor("red")
                                    c3p2.set_facecolor("red")
                                elif t < coil_3.shut_down_time:
                                    c3p1.set_facecolor("green")
                                    c3p2.set_facecolor("green")
                            if sequential_firing:
                                if coil_1.power_on_time <= t < coil_1.shut_down_time:
                                    c1p1.set_facecolor("green")
                                    c1p2.set_facecolor("green")
                                else:
                                    c1p1.set_facecolor("red")
                                    c1p2.set_facecolor("red")
                                if coil_2.power_on_time <= t < coil_2.shut_down_time:
                                    c2p1.set_facecolor("green")
                                    c2p2.set_facecolor("green")
                                else:
                                    c2p1.set_facecolor("red")
                                    c2p2.set_facecolor("red")
                                if coil_3.power_on_time <= t < coil_3.shut_down_time:
                                    c3p1.set_facecolor("green")
                                    c3p2.set_facecolor("green")
                                else:
                                    c3p1.set_facecolor("red")
                                    c3p2.set_facecolor("red")

                            time_text.set_text("Time: " + str(round(i*delta_t,decimals)) + " sec")
                            velocity_text.set_text("Velocity: " + str(round(vel[i], 2)) + " in/sec")
                            return patch, time_text, velocity_text, c1p1, c1p2, c2p1, c2p2, c3p1, c3p2

                        anim = FuncAnimation(fig, animate, init_func=init, frames=len(time)-1, interval=delta_t*1000, blit=True, repeat=True)

                        plt.title("Visualization of Slug Movement")
                        plt.xlabel("y-position(in)")
                        plt.ylabel("x-position(in)")

                        total_time = max(time)
                        frames = len(time)-1
                        frames_per_sec = frames/total_time
                        print("Total time:", total_time)
                        print("Frames:", frames)
                        print("Requested Frames per Second:", frames_per_sec)
                        anim.save("coil.gif", writer='pillow', fps=frames_per_sec)
                        if display_plots:
                            plt.show(block=False)
                            plt.pause(7)
                            plt.close()


                    animate_force_plot()
                    animate_pos_plot()
                    animate_vel_plot()
                    animate_coil_plot()
                    output_arr_local = [model_type, volt, num_turns, starting_pos, coil_2_threshold_dist, coil_3_threshold_dist, max(vel), exit_velocity]
                    output_arr_master.append(output_arr_local)

# Add all of the data to the CSV, should improve later to do it incrementally in the case of crashing/data loss
with open('batchrun.csv', 'w', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(output_arr_master)
print("Total Execution time:", str(time_module.time()-start_time))
