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

# README
# Hello! Good luck with this project. Feel free to reach out to me at nathan.wetherell2@gmail.com or by phone at 860-836-3129 if you have any questions about the code, physical rig design, 3D models, or experimental/numerical data
# This code works to generate coil timings and expected exit velocity given different mass, voltage, coil distance thresholds (when they turn on), drag coefficient, and starting positions
# It links with an FEMM model to do the actual magnetostatics calculation to get F_mag and the  uses the drag force using the explict equation generated using CFD or an assumed average drag coefficient
# I would recommend running this on a desktop for batch runs or testing of a particular parameter or leaving it running on a laptop overnight. A single simulation isnt too complicated but running a batch takes a while
# The key variables to change manually are the ones in the testing block below, the delta_t value, the body_loaded, water, payload_release, and possibly the projectile and coil parameters. Most others can be left alone. Again, contact me if you have any questions

start_time = time_module.time()
file_name = "batchrun.csv"  # name of data output file

# Testing block, True if testing that variable, False if not
voltage_test = False
num_turns_test = False
starting_pos_test = False
coil_2_threshold_test = False
coil_3_threshold_test = False
added_mass_test = False
drag_coeff_test = False
model_type = "actual"  # spaced, condensed, condensed with spacer, actual is the best model we have for the system and is recommended
display_plots = True
display_density_plot = False  # slow, only used for fun animations
display_animated_coil_plot = False  # runs looping animation at the end, always set to False for batch runs, good for explainations of concept

# Circuit Parameters, uses array if variable above set to True, else uses single value #
if voltage_test:
    voltage_arr = [50, 75, 100, 115, 125, 135, 145, 155, 165, 200, 300, 500]  # standard testing array: 115, 125, 135, 145, 155, 165
else:
    voltage_arr = [500]

if num_turns_test:
    num_turns_arr = [100, 200, 300, 315]
else:
    num_turns_arr = ["actual"]  # change to ["actual"] if 500, 500, 420 (as in physical rig)

# Coil Timing Arrays #
if starting_pos_test:  # location of the tip of the projectile relative to the start of coil 1
    starting_pos_arr = [-0.325, -0.25, 0, 0.25, 0.325]
else:
    starting_pos_arr = [0]  # this is achieved by using the launch spacer till it is flush with the breech hatch block

if coil_2_threshold_test:  # location of the center of the projectile relative to the start of coil 2
    coil_2_thresh_arr = np.ndarray.tolist(np.linspace(0, 2.5, 6))
else:
    coil_2_thresh_arr = [2]  # 1.75 for dry, 2 for submerged, optimal for test cases, could be further optimized later

if coil_3_threshold_test:  # location of the center of the projectile relative to the start of coil 3
    coil_3_thresh_arr = np.ndarray.tolist(np.linspace(0, 2.5, 6))
else:
    coil_3_thresh_arr = [1]  # 2 for dry, 1 for submerged, optimal for test cases, could be further optimized later

if added_mass_test:  # mass added to the projectile
    added_mass_arr = [0, 20, 40, 60, 80, 100, 200, 400, 800, 1000]  # standard testing array: 0, 20, 40, 60, 80, 100. Note: this is added mass, the base sled/payload mass is 200g so a 20g added mass would make the total mass 220g
else:
    added_mass_arr = [0]

if drag_coeff_test:
    drag_coeff_arr = [4.5, 5.0, 5.5, 6.0]
else:
    drag_coeff_arr = ["actual"]  # "actual" for drag force calculated using analytical CFD results, only validated for submerged tests

delta_t = 1  # time step in milliseconds, smaller is slower but better
delta_t = delta_t / 1000  # convert time step to seconds
decimals = (str(delta_t)[::-1].find('.'))

max_time = 1  # max time for the simulation to run too, prevents stagnation issues

# Firing Mode: Only one can be true #
sequential_cutoff = False  # turn all on at once, turn each off in order, will likely break circuit IRL (DO NOT USE)
sequential_firing = True  # turn each coil on and off in order, currently in use (USE THIS ONE)
manual_timings = False  # give manual timings for sequential firing of coils, good for testing and validation

if manual_timings:
    timing_arr = [43, 40.5, 43, 11.5, 6]  # in ms [coil_1_duration, coil_2_duration, coil_3_duration, coil_1_2_delay, coil_2_3_delay]
    timing_arr = [timing / 1000 for timing in timing_arr]  # convert ms to s
else:
    timing_arr = [0, 0, 0, 0, 0]

if num_turns_arr == ["actual"] and sequential_cutoff:
    print("WARNING: Sequential Cutoff Not Validated for Actual Number of Turns(500, 500, 420)")
    print("Please retry with constant turn numbers")
    quit()

# Drag Parameters #

body_loaded = True  # Whether the cylindrical body is loaded into the sled or if the system is being dry fired (
water = True  # for submerged testing water = True, for dry water = False
payload_release = True  # release payload at last coil
if water:
    fluid_density = 1000  # kg/m^3, water
else:
    fluid_density = 1.225  # kg/m^#, air

proj_cross_sec = 2.505 * (0.0254 ** 2)  # cross sectional area of payload/sled in m^2
payload_cross_sec = 1.31104 * (0.0254 ** 2)  # cross sectional area of payload in m^2
payload_drag_coeff = 0.2708  # drag_coeff of payload only, found to be 0.2708 using CFD

if drag_coeff_arr == ["actual"] and not water:
    print("CFD Drag Coefficient Array Only Validated for Water")
    quit()

# Friction Parameters #

mu = 0.01  # coefficient of dynamic friction, 0.5 for sliding PLA on steel, very low for rolling (0.01)
mu_s = 1.0  # coefficient of static friction, 1.0 for sliding PLA on steel, N/A for rolling

header = ["Model Type", "Test Type", "Voltage", "Turns", "Added Mass", "Drag Coefficient",
          "Starting Distance of Tip From Coil 1", "Coil 2 Distance Threshold", "Coil 3 Distance Threshold",
          "Coil 1 Duration", "Coil 2 Duration", "Coil 3 Duration", "Coil 1-2 Delay", "Coil 2-3 Delay", "Max Velocity",
          "Exit Velocity"]

output_arr_master = []  # array for storing the output data for the batchrun.csv file

print("Voltage Array:", voltage_arr)
print("Num Turns Array:", num_turns_arr)
print("Starting Position Array", starting_pos_arr)
print("Coil 2 Threshold Array", coil_2_thresh_arr)
print("Coil 3 Threshold Array", coil_3_thresh_arr)
print("Added Mass Array", added_mass_arr)
print("Drag Coefficient Array", drag_coeff_arr)

num_combos = len(voltage_arr) * len(num_turns_arr) * len(starting_pos_arr) * len(coil_2_thresh_arr) * len(
    coil_3_thresh_arr) * len(added_mass_arr) * len(drag_coeff_arr)
print("Number of testing combos:", num_combos)
test_num = 0


def main_function(volt, num_turns, starting_pos, coil_2_threshold_dist, coil_3_threshold_dist, added_mass, drag_coeff):  # main funner function
    print("Test:", test_num)
    if num_turns == "actual":  # 500, 500, 420
        coil_1_turns, coil_2_turns, coil_3_turns = 500, 500, 420
    else:
        coil_1_turns, coil_2_turns, coil_3_turns = num_turns, num_turns, num_turns

    if model_type == "actual":
        if volt == 165:
            coil_1_voltage = 165
            coil_2_voltage = 165
            coil_3_voltage = 165
        elif volt == 155:
            coil_1_voltage = 155
            coil_2_voltage = 155
            coil_3_voltage = 155
        else:
            coil_1_voltage = coil_2_voltage = coil_3_voltage = volt
    else:
        coil_1_voltage = coil_2_voltage = coil_3_voltage = volt

    if water:
        test_type = "Submerged"
    else:
        test_type = "Dry"
    print("\nModel Type", model_type, "Test Type", test_type, "Voltage", volt, "Number of Turns", num_turns,
          "Added Mass", added_mass, "Starting Distance From Tip to Coil 1:", starting_pos, "Coil 2 Threshold Dist:",
          coil_2_threshold_dist,
          "Coil 3 Threshold Dist:", coil_3_threshold_dist)

    current_directory = os.getcwd()  # get current working directory for file creation

    femm.openfemm()  # opens and initializes FEMM

    # Model Information - could move outside #
    if model_type == "condensed":  # OLD was for testing
        model = "ThreeCoilModelAxi.fem"
    elif model_type == "spaced":  # OLD was for testing
        model = "ThreeCoilModelAxi_Spaced.fem"
    elif model_type == "actual":  # used most of the time
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

    test_folder_path = "Test Data/" + str(volt) + "Volts-" + str(num_turns) + "Turns-" + model_type + "-" + str(
        round(starting_pos, 3)) + "in-" + str(round(coil_2_threshold_dist, 3)) + "in-" + str(
        round(coil_3_threshold_dist, 3)) + "in-" + str(datetime.now().strftime("%B-%d-%Y-%H-%M-%S"))
    final_directory = os.path.join(current_directory, test_folder_path)
    if not os.path.exists(final_directory):
        os.makedirs(final_directory)

    # Projectile Parameters: ALL REFER TO THE SLUG EXCEPT FOR MASS WHERE IT IS A COMBINATION OF SLUG, SLED, AND BODY
    # proj_r = 0.357  # radius of projectile in inches
    # proj_l = 1.3  # length of projectile in inches
    # proj_vol = np.pi * (proj_r ** 2) * proj_l  # volume of projectile in in^3
    # proj_vol = proj_vol * 1.63871e-5  # volume of projectile in m^3
    # proj_density = 7800  # density of iron in kg/m^3
    # slug_mass = proj_density * proj_vol
    slug_l = 1.3  # length of slug in inches
    slug_mass = 60 / 1000
    print("Slug mass:", slug_mass)
    sled_mass = 50 / 1000
    body_mass = 90.0 / 1000 + added_mass / 1000

    if body_loaded:  # if the cylindrical body is in the sled or just dry launching the sled
        proj_mass = slug_mass + sled_mass + body_mass
        print("Proj mass", proj_mass)
    else:
        proj_mass = slug_mass + sled_mass
    if water:
        proj_mass += 10 / 1000  # mass of water in internal baffles

    print("Effective Projectile Mass:", proj_mass, "kg")

    # Coil Parameters
    coil_radius = 1.7345  # coil radius in inches
    coil_circumference = 2 * np.pi * coil_radius
    coil_circumference = 12.67
    print("circumference:", coil_circumference)
    r_per_in = 6.385 / (1000 * 12)  # the resistance per inch of cable
    r_resistor = 1.8  # resistance of parallel discharge resistors
    c = 30 / 1000  # capacitance of each capacitor (default is 30000uF, 30mF, or 0.03F)

    if model_type == "condensed":  # model where coils are pressed up against each other
        coil_1_start_location = 1.5
        simulation_file_proj_center_start_y = 1.5
    elif model_type == "spaced":  # model where coils are significantly spaced
        coil_1_start_location = -1.5
        simulation_file_proj_center_start_y = -1.5
    elif model_type == "actual":  # model where coils are in their physical configuration
        coil_1_start_location = 1
        simulation_file_proj_center_start_y = 1
    else:
        simulation_file_proj_center_start_y = 0
        coil_1_start_location = 0
        print("Improper model_type. Must be either actual, condensed, or spaced")
        quit()
    simulation_file_proj_tip_start_y = simulation_file_proj_center_start_y + slug_l / 2

    change_in_proj_tip_start_y = starting_pos - simulation_file_proj_tip_start_y + coil_1_start_location

    if change_in_proj_tip_start_y != 0:
        print("Moving tip of projectile", starting_pos, "inches from the start of coil 1 a change of",
              round(change_in_proj_tip_start_y, decimals), "inches")

    femm.mi_seteditmode('group')
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, change_in_proj_tip_start_y)

    # proj_center_start_y = 1.5
    proj_center_start_y = starting_pos - slug_l / 2 + coil_1_start_location
    proj_center_end_y = 13.5
    if water:
        proj_center_end_y = 10
    v = 0  # initial velocity in in/sec

    proj_curr_y = proj_center_start_y
    time = []
    current_arr = []
    latest_time = 0
    time_since_coil_activation = 0

    config_dict = {'Model': model, "Test Type": test_type, "Voltage": volt, "Num Turns": num_turns,
                   "Starting Position": proj_center_start_y, "Coil 2 Threshold Distance": coil_2_threshold_dist,
                   "Coil 3 Threshold Distance": coil_3_threshold_dist, 'Slug Length': slug_l, 'Slug Mass': slug_mass,
                   'Projectile Mass': proj_mass,
                   'Proj Center Start': proj_center_start_y, 'Max Time': max_time, "Delta-T": delta_t}

    json_output = json.dumps(config_dict)
    config_path = test_folder_path + "/config_dict.json"
    f = open(config_path, "w")
    f.write(json_output)
    f.close()

    # 5, 7.5 for Air
    # 1.5, 2.5 for Coil 1 - Group 2, Coil Center at y = 2.5 (r_center,z_center)
    # 1.5, 5.5 for Coil 2 - Group 3, Coil Center at y = 5
    # 1.5, 7.5 for Coil 3 - Group 4, Coil Center at y = 7.5

    class Coil:  # coil class for storing of coil parameters such as the timings, positions, and electrical parameters
        def __init__(self, num, x_center, y_center, turns, group, on, shut_down_time, power_on_time, init_voltage):
            self.num = num
            self.x_center = x_center
            self.y_center = y_center
            self.turns = turns
            self.resistance = r_per_in * turns * coil_circumference
            if model_type == "actual":
                if num == 1:
                    self.resistance = 3.7
                elif num == 2:
                    self.resistance = 3.8
                elif num == 3:
                    self.resistance = 3.0
            self.init_voltage = init_voltage
            self.init_curr = self.init_voltage / (self.resistance + r_resistor)
            self.group = group
            self.on = on
            self.shut_down_time = shut_down_time
            self.power_on_time = power_on_time

    if model_type == "condensed":
        coil_1 = Coil(1, 1.7345, 2.5, coil_1_turns, 2, True, 0, 0, coil_1_voltage)
        coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1, coil_2_voltage)
        coil_3 = Coil(3, 1.7345, 7.5, coil_3_turns, 4, True, 0, -1, coil_3_voltage)
    elif model_type == "spaced":
        coil_1 = Coil(1, 1.7345, -0.5, coil_1_turns, 2, True, 0, 0, coil_1_voltage)
        coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1, coil_2_voltage)
        coil_3 = Coil(3, 1.7345, 10.5, coil_3_turns, 4, True, 0, -1, coil_3_voltage)
    elif model_type == "actual":  # note, x_center, y_center,, etc. are based on physical rig and the 3D model, changing the rig configuration will necessitate changing the FEMM model and these values
        coil_1 = Coil(1, 1.7345, 2, coil_1_turns, 2, True, 0, 0, coil_1_voltage)
        coil_2 = Coil(2, 1.7345, 5, coil_2_turns, 3, True, 0, -1, coil_2_voltage)
        coil_3 = Coil(3, 1.7345, 8, coil_3_turns, 4, True, 0, -1, coil_3_voltage)
    else:
        coil_1, coil_2, coil_3 = [], [], []
        print("Improper model_type. Must be either actual, condensed, or spaced")
        quit()

    coils = [coil_1, coil_2, coil_3]

    def coil_initialization():  # turn on the coils and set their correct number of turns
        for coil in coils:
            femm.mi_selectlabel(coil.x_center, coil.y_center)
            femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group, coil.turns)  # positive loop for right
            coil.on = True
            femm.mi_clearselected()
        if manual_timings:
            c1_d, c2_d, c3_d, c12_d, c23_d = timing_arr
            coil_1.power_on_time = 0
            coil_1.shut_down_time = coil_1.power_on_time + c1_d
            coil_2.power_on_time = c1_d + c12_d
            coil_2.shut_down_time = coil_2.power_on_time + c2_d
            coil_3.power_on_time = coil_2.shut_down_time + c23_d
            coil_3.shut_down_time = coil_3.power_on_time + c3_d

    coil_initialization()

    def sequential_firing_check():  # function to turn on and cut off coils in sequence, only coil 1 starts on
        nonlocal time_since_coil_activation
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
                    if proj_curr_y + slug_l / 2 >= coil.y_center - coil_threshold_dist:
                        femm.mi_selectlabel(coil.x_center, coil.y_center)
                        femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group,
                                             coil.turns)  # negative loop for left, positive loop for right
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

    def sequential_cutoff_check():  # function to turn off coils in sequence, all start on, will probably destory circuit IRL but interesting thought experiment
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
                femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group,
                                     coil.turns)  # negative loop for left, positive loop for right
                print("Coil", str(coil.num), "turned on")
                coil.on = True
            femm.mi_clearselected()

    def manual_timings_check(current_time):   # function for manual timing of coils, uses manual input array
        nonlocal time_since_coil_activation
        current_coil = 0
        if current_time < coil_1.shut_down_time:
            current_coil = 1
        elif coil_2.power_on_time <= current_time < coil_2.shut_down_time:
            current_coil = 2
        elif coil_3.power_on_time <= current_time < coil_3.shut_down_time:
            current_coil = 3
        for coil in coils:
            if coil.num == current_coil:  # if the coil is the current coil
                if not coil.on:  # turn it on if its on on already
                    femm.mi_selectlabel(coil.x_center, coil.y_center)
                    femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group,
                                         coil.turns)  # negative loop for left, positive loop for right
                    femm.mi_clearselected()
                    coil.power_on_time = time[-1]
                    print("Coil", str(coil.num), "turned on")
                    coil.on = True
                    time_since_coil_activation = 0
            elif coil.num != current_coil and coil.on:  # used for the initial proper setting
                femm.mi_selectlabel(coil.x_center, coil.y_center)
                femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                print("Coil", str(coil.num), "turned off")
                coil.on = False
            femm.mi_clearselected()
        femm.mi_clearselected()

    # Main Loop #

    payload_is_released = False
    global proj_cross_sec
    orig_cross_sec = proj_cross_sec
    orig_proj_mass = proj_mass
    orig_drag_coeff = drag_coeff

    while proj_curr_y < proj_center_end_y and latest_time < max_time:

        # Check to see if any of the coils should be turned off/on
        if sequential_firing:
            sequential_firing_check()

        elif sequential_cutoff:
            sequential_cutoff_check()

        elif manual_timings:
            manual_timings_check(latest_time)

        any_coils_on = False
        voltage = 0
        last_coil_y_center = 0
        for coil in coils:
            if coil.on:
                any_coils_on = True
                on_coil = coil.num
                r = coil.resistance + r_resistor
                voltage = coil.init_voltage * np.exp(
                    -time_since_coil_activation / (r * c))  # voltage due to discharging capacitors
            last_coil_y_center = coil.y_center

        if proj_curr_y >= last_coil_y_center and not payload_is_released and payload_release:
            print("\n--------Payload Released--------\n")
            payload_is_released = True
            proj_cross_sec = payload_cross_sec
            proj_mass = body_mass
            drag_coeff = payload_drag_coeff

        # print("Resistance:", r)
        # print("Voltage:", voltage, "Volts")
        if voltage != 0:
            current = round(voltage / r, decimals)  # current through coils
        else:
            current = 0
        current_arr.append(current)
        # print("Voltage:", voltage, "Resistance:", r, "Current:", current)
        # print("Current:", current, "Amps")
        femm.mi_modifycircprop("New Circuit", 1, current)  # propnum = 1 is the total current, change the current in FEMM

        femm.mi_seteditmode('group')  # select groups of points/lines
        if any_coils_on:  # if any coils are on, run the FEMM simulation and get force on slug
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
            if drag_coeff != "actual" or payload_is_released or not water:
                drag_force_y = 1 / 2 * drag_coeff * fluid_density * ((vel[-1] * 0.0254) ** 2) * proj_cross_sec
            else:
                drag_force_y = 0.00328 * vel[-1] ** 2 - 0.00134 * vel[-1]
                # print("\nvelocity (in/s)", vel[-1])
                # print("CFD Drag Force:", drag_force_y)
                # drag_force_cc = 1 / 2 * 5.95 * fluid_density * ((vel[-1] * 0.0254) ** 2) * proj_cross_sec
                # print("Single Drag Coeff Drag Force:", drag_force_cc)
        else:  # drag force is 0 at time 0, breaks otherwise
            time.append(0)
            drag_force_y = 0
        latest_time += delta_t  # increment the time step
        latest_time = round(latest_time, decimals)  # round time to speed up code
        # print("Time (ms):", latest_time*1000)
        time_since_coil_activation += delta_t  # modify the time since coil activation for keeping track of the current
        # print("DRAG FORCE:", drag_force_y)
        coil_force.append(force_y)  # coil force array for plotting purposes

        drag_force.append(drag_force_y)  # drag force array for plotting purposes
        # print("Drag Force", drag_force_y, "N")

        force_y += -drag_force_y  # CHANGE LATER SINCE THIS IS NOT THE CASE

        # Calculate Dynamic Frictional Forces #
        if round(v, 2) == 0:
            friction_force = 0
        elif v > 0:
            friction_force = - mu * proj_mass * 9.81
        else:  # v < 0
            friction_force = mu * proj_mass * 9.81

        # print("Force y:", force_y, "Friction Force:", friction_force)
        force_y += friction_force  # positive and negative are taken care of in the frictional force
        # print("New force y:", force_y)

        # Determine acceleration, delta-v, and delta-pos #
        acc = force_y / proj_mass  # a=F/m
        # print("acceleration (m/s)", acc)
        acc = 39.3701 * acc  # acceleration of the projectile in in/s^2
        # print("acceleration (in/s)", acc)
        # print("Acceleration:", acc, "in/s^2")
        delta_v = acc * delta_t  # dv=a*dt
        # print("delta-v", delta_v)
        # print("Delta-v:", delta_v, "in/s")
        v += delta_v
        vel.append(v)  # velocity array for plotting purposes

        proj_curr_y += v * delta_t + 0.5 * acc * delta_t * delta_t  # based on kinematic equation dX = v_0*t+1/2*a*t^2

        # v += delta_v  #
        # print("Current Velocity:", v)
        femm.mo_clearblock()
        femm.mo_hidedensityplot()
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(0, v * delta_t + 0.5 * acc * delta_t * delta_t)  # move the object in FEMM
        if display_density_plot:
            femm.mo_showdensityplot(1,0, 0,1.5,'bmag')
        femm.mo_clearblock()

    femm.mi_close()  # close postprocessor
    femm.closefemm()  # close entire FEMM window
    proj_cross_sec = orig_cross_sec
    proj_mass = orig_proj_mass
    drag_coeff = orig_drag_coeff

    coil_force = np.array(coil_force)  # convert to numpy array for efficient data processing
    pos = np.array(pos)

    # Export block

    for coil in coils:  # get the pulse duration for each coil from its start and end time, report out
        pulse_duration = round(coil.shut_down_time - coil.power_on_time, decimals)
        if coil.num == 1:
            print("Coil", coil.num, "pulse duration:", pulse_duration * 1000, "ms from", coil.power_on_time * 1000,
                  "to",
                  coil.shut_down_time * 1000, "ms")
        else:
            print("Coil", coil.num, "pulse duration:", pulse_duration * 1000, "ms from", coil.power_on_time * 1000,
                  "to",
                  coil.shut_down_time * 1000, "ms. A delay of",
                  round(coil.power_on_time - coils[coil.num - 2].shut_down_time, decimals) * 1000,
                  "ms since last shutoff")

    coil_1_pulse_duration = round(coil_1.shut_down_time - coil_1.power_on_time, decimals) * 1000  # ms
    coil_2_pulse_duration = round(coil_2.shut_down_time - coil_2.power_on_time, decimals) * 1000  # ms
    coil_3_pulse_duration = round(coil_3.shut_down_time - coil_3.power_on_time, decimals) * 1000  # ms
    coil_1_2_pulse_delay = round(coil_2.power_on_time - coil_1.shut_down_time, decimals) * 1000  # ms
    coil_2_3_pulse_delay = round(coil_3.power_on_time - coil_2.shut_down_time, decimals) * 1000  # ms
    # exit velocity defined as when the slug center reaches 12.85 in the actual model dry or 8 in the actual model submerged (pulled back by final coil)
    full_exit_index = 0
    exit_time = 0
    for x in pos:
        if x > 12.85 and not water:  # 12.85 is when slug is leaving
            full_exit_index = (np.where(pos == x))[0][0]
            exit_time = time[full_exit_index]
            break
        elif x > 8.6 and water:  # 8 at the center of the last coil, 8.6 when projectile is just peaking out
            full_exit_index = (np.where(pos == x))[0][0]
            exit_time = time[full_exit_index]
            break
    exit_velocity = vel[full_exit_index]
    print("Expected Exit Velocity:", exit_velocity, "in/s")
    output_dict = {"Max Velocity (in/s)": max(vel), "Exit Velocity": exit_velocity,
                   "Coil 1 Pulse Duration": coil_1_pulse_duration, "Coil 1 Pulse Start": coil_1.power_on_time,
                   "Coil 1 Pulse Stop": coil_1.shut_down_time, "Coil 2 Pulse Duration": coil_2_pulse_duration,
                   "Coil 2 Pulse Start": coil_2.power_on_time, "Coil 2 Pulse Stop": coil_2.shut_down_time,
                   "Coil 3 Pulse Duration": coil_3_pulse_duration, "Coil 3 Pulse Start": coil_3.power_on_time,
                   "Coil 3 Pulse Stop": coil_3.shut_down_time}
    print(output_dict)

    # JSON output #
    json_output = json.dumps(output_dict)
    output_path = test_folder_path + "/output.json"
    f = open(output_path, "w")
    f.write(json_output)
    f.close()

    anim_frames = min(len(time) - 1, 100)  # number of frames for the animations

    # Plotting block

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
        ax.set_ylim(lower_bound, max(coil_force) * 1.1)
        ax2.set_ylim(0, max(current_arr) * 1.1)

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
            ax.add_patch(Rectangle((coil.power_on_time, lower_bound), coil.shut_down_time - coil.power_on_time,
                                   max(coil_force) * 1.1, color=line_color, alpha=0.5, label=label_string))

        fig_path = test_folder_path + "/coil_force.png"

        def animation_function(i):
            i_orig = i
            i = int(i * len(time) / anim_frames)
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

        animation = FuncAnimation(figure, func=animation_function, interval=50, frames=anim_frames, blit=False,
                                  repeat=False)
        ax.legend(loc="upper right")
        ax2.legend(loc="upper left")
        if display_plots:
            plt.show(block=False)
            plt.pause(7)
            plt.close()

    def animate_pos_plot():  # does what it says on the tin
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
        ax.set_ylim(lower_bound, max(pos) * 1.1)

        # Since plotting a single graph
        line, = ax.plot(0, 0)

        fig_path = test_folder_path + "/pos.png"

        def animation_function(i):
            i_orig = i
            i = int(i * len(time) / anim_frames)
            time_plt.append(time[i])
            pos_plt.append(pos[i])

            line.set_xdata(time_plt)
            line.set_ydata(pos_plt)

            if i_orig == anim_frames - 1:
                plt.savefig(fig_path)
            return line,

        animation = FuncAnimation(figure, func=animation_function, interval=50, frames=anim_frames, blit=False,
                                  repeat=False)
        if display_plots:
            plt.show(block=False)
            plt.pause(7)
            plt.close()

    def animate_vel_plot():  # does what it says on the tin
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
        ax.set_ylim(lower_bound, max(vel) * 1.1)

        # Since plotting a single graph
        line, = ax.plot(0, 0)

        fig_path = test_folder_path + "/vel.png"
        ax.axvline(x=exit_time, color="green", label="Expulsion")

        def animation_function(i):
            i_orig = i
            i = int(i * len(time) / anim_frames)
            time_plt.append(time[i])
            vel_plt.append(vel[i])

            line.set_xdata(time_plt)
            line.set_ydata(vel_plt)
            if i_orig == anim_frames - 1:
                plt.savefig(fig_path)
            return line,

        animation = FuncAnimation(figure, func=animation_function, interval=50, frames=anim_frames, blit=False,
                                  repeat=False)
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

        time_text = ax.text(0.65, 0.9, "Time Text", bbox={'facecolor': 'black', 'alpha': 0, 'pad': 1},
                            transform=ax.transAxes, ha="left", color="white", fontsize=12)
        velocity_text = ax.text(0.65, 0.85, "Velocity Text", bbox={'facecolor': 'black', 'alpha': 0, 'pad': 1},
                                transform=ax.transAxes, ha="left", color="white", fontsize=12)

        lower_bound = min(pos)
        if lower_bound <= 0:
            lower_bound = lower_bound * 1.1 - slug_l
        else:
            lower_bound = lower_bound / 1.1 - slug_l

        # Setting limits for x and y axis
        ax.set_xlim(-10, 10)
        ax.set_ylim(lower_bound, max(pos) * 1.1 + slug_l)
        patch = plt.Rectangle((0 - slug_l, 0), width=slug_l * 2, height=slug_l, fc="grey")

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
            patch.set_y(y - slug_l / 2)

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

            time_text.set_text("Time: " + str(round(i * delta_t, decimals)) + " sec")
            velocity_text.set_text("Velocity: " + str(round(vel[i], 2)) + " in/sec")
            return patch, time_text, velocity_text, c1p1, c1p2, c2p1, c2p2, c3p1, c3p2

        anim = FuncAnimation(fig, animate, init_func=init, frames=len(time) - 1, interval=delta_t * 1000, blit=True,
                             repeat=True)

        plt.title("Visualization of Slug Movement")
        plt.xlabel("y-position(in)")
        plt.ylabel("x-position(in)")

        total_time = max(time)
        frames = len(time) - 1
        frames_per_sec = frames / total_time
        print("Total time:", total_time)
        print("Frames:", frames)
        print("Requested Frames per Second:", frames_per_sec)
        anim.save("coil.gif", writer='pillow', fps=frames_per_sec)
        if display_plots:
            plt.show(block=False)
            plt.pause(7)
            plt.close()

    if display_plots:
        animate_force_plot()
        animate_pos_plot()
        animate_vel_plot()
    if display_animated_coil_plot:
        animate_coil_plot()
    output_arr_local = [model_type, test_type, volt, num_turns, added_mass, drag_coeff, starting_pos,
                        coil_2_threshold_dist, coil_3_threshold_dist, coil_1_pulse_duration, coil_2_pulse_duration,
                        coil_3_pulse_duration, coil_1_2_pulse_delay, coil_2_3_pulse_delay,
                        max(vel), exit_velocity]
    output_arr_master.append(output_arr_local)


# Main testing loops (nested)#
for volt in voltage_arr:
    for num_turns in num_turns_arr:
        for starting_pos in starting_pos_arr:
            for coil_2_threshold_dist in coil_2_thresh_arr:
                for coil_3_threshold_dist in coil_3_thresh_arr:
                    for added_mass in added_mass_arr:
                        for drag_coeff in drag_coeff_arr:
                            test_num += 1
                            main_function(volt, num_turns, starting_pos, coil_2_threshold_dist, coil_3_threshold_dist,
                                          added_mass, drag_coeff)

# Add all of the data to the CSV, should improve later to do this incrementally in the case of crashing/data loss
with open(file_name, 'a+', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(output_arr_master)
print("Total Execution time:", str(time_module.time() - start_time))
