import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def draw_labeled_box(ax, x, y, z, dx, dy, dz, color='skyblue', label=''):
    verts = [
        [(x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z)],
        [(x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)],
        [(x, y, z), (x, y, z + dz), (x, y + dy, z + dz), (x, y + dy, z)],
        [(x + dx, y, z), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x + dx, y + dy, z)],
        [(x, y, z), (x, y, z + dz), (x + dx, y, z + dz), (x + dx, y, z)],
        [(x, y + dy, z), (x, y + dy, z + dz), (x + dx, y + dy, z + dz), (x + dx, y + dy, z)]
    ]
    ax.add_collection3d(Poly3DCollection(verts, facecolors=color, edgecolors='black', alpha=1.0))

    fontsize = 8
    # ตำแหน่งของข้อความที่จะแสดงติดกับผิวของกล่อง
    ax.text(x + dx / 2, y + dy / 2, z + dz / 2, label, ha='center', va='center', fontsize=fontsize, color='black')

colors = {
    'Sky Blue': 'skyblue',
    'Light Green': 'lightgreen',
    'Light Coral': 'lightcoral',
    'Plum': 'plum'
}
labels = list(colors.keys())
color_values = list(colors.values())

fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')

for i in range(3):
    for j in range(2):
        index = (i + j) % len(color_values)
        draw_labeled_box(
            ax,
            x=i * 1.1,
            y=j * 1.1,
            z=0,
            dx=1,
            dy=1,
            dz=1,
            color=color_values[index],
            label=labels[index]
        )

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_xlim(0, 4)
ax.set_ylim(0, 3)
ax.set_zlim(0, 2)
plt.tight_layout()
plt.show()
