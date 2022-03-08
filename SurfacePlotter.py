import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import axes3d

# Read CSV
csvFileName = "surface_plot.csv"
csvData = []
with open(csvFileName, 'r') as csvFile:
    csvReader = csv.reader(csvFile, delimiter=',')
    for csvRow in csvReader:
        csvData.append(csvRow)

# Get X, Y, Z
csvData = np.array(csvData)
csvData = csvData.astype(float)
X, Y, Z = csvData[:,1], csvData[:,2], csvData[:,4]

# Plot X,Y,Z
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_trisurf(X, Y, Z, color='white', edgecolors='grey', alpha=0.5, cmap=cm.coolwarm)
ax.scatter(X, Y, Z, c='red', s=1)

plt.title("Submegered Exit Velocity Versus Threshold Distances for 160-Volt Coils 0.315 in Starting Distance")
ax.set_xlabel("Coil 2 Threshold Distance (in)")
ax.set_ylabel("Coil 3 Threshold Distance (in)")
ax.set_zlabel('Exit Velocity (in/s)')
cbar = fig.colorbar(surf, shrink=0.5, aspect=5)
cbar.ax.set_ylabel('Exit Velocity(in/s)', rotation=90)
plt.show()