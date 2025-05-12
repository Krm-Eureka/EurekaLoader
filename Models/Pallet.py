import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from tkinter import messagebox, filedialog

class Pallet:
    def __init__(self, width, length, height, frame_height=None, gap=0.2):
        w = type(width)
        l = type(length)
        h = type(height)
        print(f"width={w}, length={l}, height={h}")
        self.width = int(width)
        self.length = int(length)
        self.height = int(height)
        self.frame_height = frame_height if frame_height is not None else height
        self.gap = gap
        self.boxes = []
        self.occupancy_grid = np.zeros(
            (self.width, self.length, self.height), dtype=bool
        )

    def draw_pallet_frame(self, ax):
        # messagebox.showinfo(
        #     "Pallet Frame",
        #     f"Width: {self.width}, Length: {self.length}, Height: {self.height}",
        # )
        x, y, z = 0, 0, 0
        dx, dy, dz = self.width, self.length, self.height
        vertices = np.array(
            [
                [x, y, z],
                [x + dx, y, z],
                [x + dx, y + dy, z],
                [x, y + dy, z],
                [x, y, z + dz],
                [x + dx, y, z + dz],
                [x + dx, y + dy, z + dz],
                [x, y + dy, z + dz],
            ]
        )
        edges = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],
            [4, 5],
            [5, 6],
            [6, 7],
            [7, 4],
            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7],
        ]
        ax.add_collection3d(
            Line3DCollection(
                vertices[edges], color="black", linestyle="dashed", linewidth=1
            )
        )