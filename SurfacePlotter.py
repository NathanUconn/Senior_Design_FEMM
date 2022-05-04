import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
has_header = True
# Read CSV
submerged = False
extended = True
if submerged:
    if extended:
        csvFileName = "ModelDataSubmergedExtended.csv"
    else:
        csvFileName = "ModelDataSubmerged.csv"
else:
    if extended:
        csvFileName = "ModelDataDryExtended.csv"
    else:
        csvFileName = "ModelDataDry.csv"
csvData = []
with open(csvFileName, 'r') as csvFile:
    csvReader = csv.reader(csvFile, delimiter=',')
    row_num = 0
    for csvRow in csvReader:
        if has_header and row_num == 0:
            print("Skipping header")
        else:
            csvData.append(csvRow)
        row_num += 1
# C(V),E(M),P(vel)
# Get X, Y, Z
csvData = np.array(csvData)
csvData = csvData.astype(float)
X, Y, Z = csvData[:,0], csvData[:,1], csvData[:,12]
voltages, added_masses = [], []
for i in X:
    if i not in voltages:
        voltages.append(i)
for i in Y:
    if i not in added_masses:
        added_masses.append(i)


num_voltages = len(voltages)
num_masses = len(added_masses)
print("Num voltages:", num_voltages)
print("Num added masses:", added_masses)
# ARRAY VERSION
voltage_exit_vel_arr = []

for voltage in voltages:
    arr = []
    index = 0
    for entry in X:
        if entry == voltage:
            arr.append(Z[index])
        index += 1
    voltage_exit_vel_arr.append(arr)
print(voltage_exit_vel_arr)

added_mass_exit_vel_arr = []

for added_mass in added_masses:
    arr = []
    index = 0
    for entry in Y:
        if entry == added_mass:
            arr.append(Z[index])
        index += 1
    added_mass_exit_vel_arr.append(arr)
print(added_mass_exit_vel_arr)

# Plot Voltage,Exit Velocity

fig = plt.figure(figsize=(12,10))
ax = fig.add_subplot()
for j in range(len(voltage_exit_vel_arr[0])):
    vel_arr = list(list(zip(*voltage_exit_vel_arr))[j])
    plt.plot(voltages, vel_arr, ".-", markersize="15", label=(str(added_masses[j]) + " grams"))
if submerged:
    plt.title("Model Predicted Submerged Exit Velocity Versus Capacitor Voltage")
else:
    plt.title("Model Predicted Dry Exit Velocity Versus Capacitor Voltage")
ax.set_xlabel("Capacitor Voltage (volts)")
ax.set_ylabel("Exit Velocity (in/s)")
ax.legend()
ax.grid()
plt.show()
plt.cla()
plt.clf()
plt.close()

# Plot Masses vs Exit Velocity
fig = plt.figure(figsize=(12,10))
ax = fig.add_subplot()
fit_arr_x = []
fit_axx_y = []
for j in range(len(added_mass_exit_vel_arr[0])):
    vel_arr = list(list(zip(*added_mass_exit_vel_arr))[j])
    plt.plot(added_masses, vel_arr, ".-", markersize="15", label=(str(voltages[j]) + " volts"))
    if j == len(added_mass_exit_vel_arr[0])-1:
        fit_arr_x = added_masses
        fit_arr_y = vel_arr
p = np.poly1d(np.polyfit(fit_arr_x, fit_arr_y, 2))
p_x = np.linspace(0, 1000, 1000)
# plt.plot(p_x, p(p_x), '-')
if submerged:
    plt.title("Model Predicted Submerged Exit Velocity Added Mass")
else:
    plt.title("Model Predicted Dry Exit Velocity Added Mass")
ax.set_xlabel("Added Mass (grams)")
ax.set_ylabel("Exit Velocity (in/s)")
ax.legend()
ax.grid()
plt.show()
plt.cla()
plt.clf()
plt.close()





# Plot X,Y,Z
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_trisurf(X, Y, Z, color='white', edgecolors='grey', alpha=0.5, cmap=cm.coolwarm)
ax.scatter(X, Y, Z, c='red', s=1)

if submerged:
    plt.title("Model Predicted Submerged Exit Velocity Versus Capacitor Voltage and Added Mass")
else:
    plt.title("Model Predicted Dry Exit Velocity Versus Capacitor Voltage and Added Mass")
ax.set_xlabel("Capacitor Voltage (volts)")
ax.set_ylabel("Added Mass (grams)")
ax.set_zlabel('Exit Velocity (in/s)')
cbar = fig.colorbar(surf, shrink=0.5, aspect=5)
cbar.ax.set_ylabel('Exit Velocity(in/s)', rotation=90)
plt.show()