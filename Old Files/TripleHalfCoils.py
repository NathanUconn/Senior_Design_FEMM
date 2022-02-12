import femm
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import os
from datetime import datetime
import json

current_directory = os.getcwd()

femm.openfemm()
model = "ThreeHalfCoilModel.fem"
femm.opendocument(model)
femm.mi_saveas("temp.fem")
femm.mi_seteditmode("group")
pos = []
force = []
vel = []

path = "Test Data"
final_directory = os.path.join(current_directory, path)
if not os.path.exists(final_directory):
    os.makedirs(final_directory)

test_folder_path = "Test Data/" + str(datetime.now().strftime("%B-%d-%Y-%H-%M-%S"))
final_directory = os.path.join(current_directory, test_folder_path)
if not os.path.exists(final_directory):
    os.makedirs(final_directory)

# Projectile Parameters: ALL REFER TO THE SLUG EXCEPT FOR MASS WHERE IT IS A COMBINATION OF SLUG, SLED, AND BODY
proj_r = 0.357  # radius of projectile in inches
proj_l = 1.3  # length of projectile in inches
proj_vol = np.pi * (proj_r**2) * proj_l  # volume of projectile in in^3
proj_vol = proj_vol * 1.63871e-5  # volume of projectile in m^3
proj_density = 7860  # density of iron in kg/m^3
slug_mass = proj_density * proj_vol
sled_mass = 58.21/1000
body_mass = 105.42/1000

proj_mass = slug_mass/2 + sled_mass # + body_mass/2  # Divided by 2 as only half simulated

print()
print("Projectile Mass:", proj_mass, "kg")

proj_center_start_y = 1.5
proj_center_end_y = 13.5
v = 0  # initial velocity in in/sec
delta_t = 0.01  # time step in seconds

max_time = 2

sequential_cutoff = False
sequential_firing = True

proj_curr_y = proj_center_start_y
time = []
latest_time = 0
decimals = (str(delta_t)[::-1].find('.'))

config_dict = {'Model': model, 'Projectile Radius': proj_r, 'Projectile Length':  proj_l, 'Projectile Volume': proj_vol, 'Projectile Mass': proj_mass, 'Proj Center Start':  proj_center_start_y, 'Max Time': max_time, "Delta-T": delta_t}

json = json.dumps(config_dict)
config_path = test_folder_path + "/config_dict.json"
f = open(config_path, "w")
f.write(json)
f.close()

# 5, 7.5 for Air
# 1.5, 2.5 for Coil 1 - Group 2, Coil Center at y = 2.5
# 1.5, 5.5 for Coil 2 - Group 3, Coil Center at y = 5
# 1.5, 7.5 for Coil 3 - Group 4, Coil Center at y = 7.5


class Coil:
    def __init__(self, num, x_center, y_center, group, on, shut_down_time, power_on_time):
        self.num = num
        self.x_center = x_center
        self.y_center = y_center
        self.group = group
        self.on = on
        self.shut_down_time = shut_down_time
        self.power_on_time = power_on_time


coil_1 = Coil(1, 1.43, 2.5, 2, True, 0, 0)
coil_2 = Coil(2, 1.43, 5, 3, True, 0, -1)
coil_3 = Coil(3, 1.43, 7.5, 4, True, 0, -1)

coils = [coil_1, coil_2, coil_3]

while proj_curr_y < proj_center_end_y and latest_time < max_time:
    femm.mi_seteditmode('group')
    femm.mi_analyze()
    femm.mi_loadsolution()

    femm.mo_clearblock()
    femm.mo_groupselectblock(1)
    force_y = -femm.mo_blockintegral(19)
    # print("FEMM Reported Force on Slug", force_y)

    pos.append(proj_curr_y)
    if len(time) != 0:
        time.append(latest_time)
    else:
        time.append(0)
    latest_time += delta_t
    latest_time = round(latest_time, decimals)
    # print("FORCE:", force_y)
    force.append(force_y)
    acc = force_y/proj_mass  #
    acc = 39.3701 * acc  # acceleration of the projectile in in/s^2
    # print("Acceleration:", acc, "in/s^2")
    delta_v = acc * delta_t
    # print("Delta-v:", delta_v, "in/s")
    vel.append(v)

    proj_curr_y += v*delta_t + 0.5*acc*delta_t*delta_t  # based on kinematic equation deltaX = v_0*t+1/2*a*t^2

    v += delta_v
    femm.mo_clearblock()
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, v*delta_t + 0.5*acc*delta_t*delta_t)

    if sequential_firing:
        femm.mi_seteditmode('blocks')
        current_coil = 0

        for coil in coils:
            if coil.power_on_time != -1:
                current_coil = coil.num

        for coil in coils:
            femm.mi_selectlabel(coil.x_center, coil.y_center)
            if coil.num == current_coil:  # if the coil is the current coil, check to see if it is past the midpoint
                if proj_curr_y >= coil.y_center and coil.on:
                    femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                    coil.shut_down_time = time[-1]
                    # print("Coil", str(coil.num), "turned off")
                    coil.on = False
                    current_coil += 1
                elif proj_curr_y < coil.y_center and not coil.on:
                    femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group, 100)
                    coil.power_on_time = time[-1]
                    coil.on = True
            elif coil.num != current_coil and coil.on:  # used for the initial proper setting
                femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                coil.on = False
            femm.mi_clearselected()

    elif sequential_cutoff:
        femm.mi_seteditmode('blocks')
        for coil in coils:
            femm.mi_selectlabel(coil.x_center, coil.y_center)
            if proj_curr_y >= coil.y_center and coil.on:
                femm.mi_setblockprop("18 AWG", 0, 0.2, "<None>", 0, coil.group, 0)
                coil.shut_down_time = time[-1]
                # print("Coil", str(coil.num), "turned off")
                coil.on = False
            elif proj_curr_y < coil.y_center and not coil.on:
                femm.mi_setblockprop("18 AWG", 0, 0.2, "New Circuit", 0, coil.group, 100)
                # print("Coil", str(coil.num), "turned on")
                coil.on = True
        femm.mi_clearselected()

femm.closefemm()

force = np.array(force)
pos = np.array(pos)

for coil in coils:
    pulse_duration = round(coil.shut_down_time - coil.power_on_time, decimals)
    print("Coil", coil.num, "pulse duration:", pulse_duration, "seconds from", coil.power_on_time, "to", coil.shut_down_time, "seconds")


def animate_force_plot():
    time_plt = []
    force_plt = []

    figure, ax = plt.subplots()

    plt.title("Force(N) of Slug Versus Time(s)")
    plt.xlabel("Time(s)")
    plt.ylabel("Force(N)")

    # Setting limits for x and y axis
    ax.set_xlim(0, max_time)
    lower_bound = min(force)
    if lower_bound <= 0:
        lower_bound = lower_bound * 1.1
    else:
        lower_bound = lower_bound / 1.1
    ax.set_ylim(lower_bound, max(force)*1.1)

    # Since plotting a single graph
    line, = ax.plot(0, 0)

    def animation_function(i):
        time_plt.append(time[i])
        force_plt.append(force[i])

        line.set_xdata(time_plt)
        line.set_ydata(force_plt)
        return line,


    animation = FuncAnimation(figure, func = animation_function, interval=50, frames=min(len(time)-1,100), blit=True, repeat=False)
    path = os.getcwd() + "/force.gif"
    # animation.save(path, writer='imagemagick', fps=30)

    plt.show()



def animate_pos_plot():
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
    ax.set_xlim(0, max_time)
    ax.set_ylim(lower_bound, max(pos)*1.1)

    # Since plotting a single graph
    line, = ax.plot(0, 0)

    def animation_function(i):
        time_plt.append(time[i])
        pos_plt.append(pos[i])

        line.set_xdata(time_plt)
        line.set_ydata(pos_plt)
        return line,


    animation = FuncAnimation(figure, func = animation_function, interval=50, frames=min(len(time)-1,100), blit=True, repeat=False)
    plt.show()


def animate_vel_plot():
    time_plt = []
    vel_plt = []

    figure, ax = plt.subplots()

    lower_bound = min(vel)
    if lower_bound <= 0:
        lower_bound = lower_bound * 1.1
    else:
        lower_bound = lower_bound / 1.1

    # Setting limits for x and y axis
    ax.set_xlim(0, max_time)
    ax.set_ylim(lower_bound, max(vel)*1.1)

    # Since plotting a single graph
    line, = ax.plot(0, 0)

    def animation_function(i):
        time_plt.append(time[i])
        vel_plt.append(vel[i])

        line.set_xdata(time_plt)
        line.set_ydata(vel_plt)
        return line,


    animation = FuncAnimation(figure, func = animation_function, interval=50, frames=min(len(time)-1,100), blit=True, repeat=False)
    plt.title("Vel(in/s) of Slug Versus Time(s)")
    plt.xlabel("Time(s)")
    plt.ylabel("Vel(in/s)")
    plt.show()


def animate_coil_plot():
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
    plt.show()


animate_force_plot()
animate_pos_plot()
animate_vel_plot()
animate_coil_plot()
