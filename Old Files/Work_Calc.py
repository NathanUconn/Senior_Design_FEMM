import femm
import matplotlib.pyplot as plt
import numpy as np

femm.openfemm()
femm.opendocument("SecondCoilgunModel.fem");
femm.mi_saveas("temp.fem")
femm.mi_seteditmode("group")
pos=[];
force=[];

proj_r = 0.357  # radius of projectile in inches
proj_l = 1.3  # length of projectile in inches
proj_vol = np.pi * (proj_r**2) * proj_l  # volume of projectile in in^3
proj_vol = proj_vol * 1.63871e-5  # volume of projectile in m^3
proj_density = 7860  # density of iron in kg/m^3
proj_mass = proj_density * proj_vol

print("Projectile Mass:", proj_mass, "kg")

proj_center_start_y = 6.15
proj_center_end_y = 3

num_tests = 10

for n in range(0,num_tests):
    femm.mi_analyze()
    femm.mi_loadsolution()
    femm.mo_groupselectblock(1)
    fz=femm.mo_blockintegral(19)
    print("Force y", fz)
    pos.append(n*0.1)
    force.append(fz)
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, (proj_center_end_y-proj_center_start_y)/num_tests)
femm.closefemm()
# f = plt.figure()
# f.set_figwidth(4)
# f.set_figheight(1)
plt.plot(pos,force)
plt.ylabel('Force, N')
plt.xlabel('Offset, in')
plt.show()

force = np.array(force)
pos = np.array(pos)

print("Force array:", force)

# Compute the area using the composite trapezoidal rule.
work_in = np.trapz(force, pos)
work = work_in * 0.0254
print("Total Work:", work_in, "N*in or", work, "N*m")

velocity = np.sqrt(2*work*proj_mass)
print("Final velocity:", velocity, "m/s")


