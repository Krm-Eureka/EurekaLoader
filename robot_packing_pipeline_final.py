import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from typing import List, Tuple
import numpy as np
import time
import csv

GAP = 20 #mm

class Box:
    def __init__(self, length: int, width: int, height: int, sku: str, priority: int):
        self.length = length
        self.width = width
        self.height = height
        self.sku = sku
        self.priority = priority
        self.x = self.y = self.z = 0

    def set_position(self, x: int, y: int, z: int):
        self.x, self.y, self.z = x, y, z

    def get_volume(self):
        return self.length * self.width * self.height

    def collides_with(self, other) -> bool:
        return not (
            self.x + self.length <= other.x or self.x >= other.x + other.length or
            self.y + self.width <= other.y or self.y >= other.y + other.width or
            self.z + self.height <= other.z or self.z >= other.z + other.height
        )

    def is_supported(self, placed_boxes: List['Box'], pallet_height: int) -> bool:
        if self.z <= pallet_height:
            return True
        center_x = self.x + self.length / 2
        center_y = self.y + self.width / 2
        for b in placed_boxes:
            if abs(b.z + b.height - self.z) < 1e-6:
                if b.x <= center_x <= b.x + b.length and b.y <= center_y <= b.y + b.width:
                    return True
        return False

class Pallet:
    def __init__(self, width, length, height, frame_height=None, gap=0.2):
        self.width = int(width)
        self.length = int(length)
        self.height = int(height)
        self.frame_height = frame_height if frame_height is not None else height
        self.gap = gap
        self.boxes = []
        self.occupancy_grid = np.zeros((self.width, self.length, self.height), dtype=bool)

    def draw_pallet_frame(self, ax):
        x, y, z = 0, 0, 0
        dx, dy, dz = self.width, self.length, self.height
        vertices = np.array([
            [x, y, z], [x + dx, y, z], [x + dx, y + dy, z], [x, y + dy, z],
            [x, y, z + dz], [x + dx, y, z + dz], [x + dx, y + dy, z + dz], [x, y + dy, z + dz]
        ])
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],
            [4, 5], [5, 6], [6, 7], [7, 4],
            [0, 4], [1, 5], [2, 6], [3, 7]
        ]
        ax.add_collection3d(Line3DCollection(vertices[edges], color='black', linestyle='dashed', linewidth=2))

class Container:
    def __init__(self, length: int, width: int, height: int, color: str, pallet: Pallet):
        self.length = length
        self.width = width
        self.height = height
        self.color = color
        self.pallet_height = pallet.height
        self.boxes = []
        self.pallet = pallet
        self.start_x = (pallet.width - self.width) / 2
        self.start_y = (pallet.length - self.length) / 2
        self.end_x = self.start_x + self.width
        self.end_y = self.start_y + self.length
        self.end_z = self.pallet_height + (self.height - self.pallet_height)

    def can_place(self, box: Box, x: int, y: int, z: int) -> Tuple[bool, str]:
        box_end_x = x + box.length
        box_end_y = y + box.width
        box_end_z = z + box.height

        if (x < 0 or y < 0 or z < self.pallet_height or
                box_end_x > self.length or box_end_y > self.width or box_end_z > self.height):
            return False, "Out of container bounds"

        box.set_position(x, y, z)
        for placed in self.boxes:
            if box.collides_with(placed):
                return False, "Collision with another box"

        if not box.is_supported(self.boxes, self.pallet_height):
            return False, "Box not supported from below"

        return True, "OK"

    def place_box(self, box: Box):
        self.boxes.append(box)

    def generate_candidate_positions(self) -> List[Tuple[int, int, int]]:
        if not self.boxes:
            return [(int(self.start_x) + int(GAP), int(self.start_y) + int(GAP), self.pallet_height)]

        positions = []
        for b in self.boxes:
            for dx in [0, b.length]:
                for dy in [0, b.width]:
                    for dz in [0, b.height]:
                        x, y, z = b.x + dx, b.y + dy, b.z + dz
                        if self.start_x <= x < self.end_x and self.start_y <= y < self.end_y and self.pallet_height <= z < self.end_z:
                            positions.append((int(x), int(y), int(z)))
        return sorted(set(positions), key=lambda pos: (pos[2], pos[1], pos[0]))

def draw_3d_boxes(container: Container):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    container.pallet.draw_pallet_frame(ax)
    draw_container(ax, container)
    for box in container.boxes:
        draw_box(ax, box)
    ax.set_xlim([0, container.pallet.width])
    ax.set_ylim([0, container.pallet.length])
    ax.set_zlim([0, container.height])

    ax.set_xlabel('X (Width mm)')
    ax.set_ylabel('Y (Length mm)')
    ax.set_zlabel('Z (Height mm)')

    plt.show()

def draw_container(ax, container: Container):
    x, y, z = container.start_x, container.start_y, container.pallet_height
    dx, dy, dz = container.length, container.width, container.height - container.pallet_height
    vertices = np.array([
        [x, y, z], [x + dx, y, z], [x + dx, y + dy, z], [x, y + dy, z],
        [x, y, z + dz], [x + dx, y, z + dz], [x + dx, y + dy, z + dz], [x, y + dy, z + dz]
    ])
     # เลือกเฉพาะ 5 ด้าน (ไม่รวมด้านบน)
    faces = [
        [0, 1, 2, 3],  # ด้านล่าง
        [0, 1, 5, 4],  # ด้านหน้า
        [1, 2, 6, 5],  # ด้านขวา
        [2, 3, 7, 6],  # ด้านหลัง
        [3, 0, 4, 7]   # ด้านซ้าย
    ]
    ax.add_collection3d(Poly3DCollection(vertices[faces], facecolors='blue', linewidths=1, edgecolors='black', alpha=0.1))

def draw_box(ax, box: Box):
    x, y, z = box.x, box.y, box.z
    dx, dy, dz = box.length, box.width, box.height
    vertices = np.array([
        [x, y, z], [x + dx, y, z], [x + dx, y + dy, z], [x, y + dy, z],
        [x, y, z + dz], [x + dx, y, z + dz], [x + dx, y + dy, z + dz], [x, y + dy, z + dz]
    ])
    faces = [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]
    ]
    # กำหนดสีตาม SKU
    sku_colors = {
    "C1": "red",
    "C2": "green",
    "C3": "blue",
    "C4": "yellow",
    "C5": "orange",
    "C6": "purple",
    "C7": "cyan",
    "C8": "magenta",
    "C9": "lime",
    "C10": "teal",
    "C11": "maroon",
    "C12": "navy",
    "C13": "olive",
    "C14": "silver",
    "C15": "gold",
    "C16": "coral",
    "C17": "indigo",
    "C18": "violet",
    "C19": "turquoise",
    "C20": "pink",
    "C21": "brown",
    "C22": "aquamarine",
    "C23": "chartreuse",
    "C24": "khaki",
    "C25": "lavender",
    "C26": "salmon",
    "C27": "tan",
    "C28": "plum",
    "C29": "beige",
    "C30": "crimson",
    "C31": "darkgreen",
    "C32": "darkblue",
    "C33": "darkred",
    "C34": "darkorange",
    "C35": "darkcyan",
    "C36": "darkmagenta",
    "C37": "darkkhaki",
    "JP1": "lightcoral",
    "JP2": "lightgreen",
    "JP3": "lightblue",
    "C38": "lightyellow",
    "C39": "lightsalmon",
    "C40": "lightpink",
    "C41": "lightcyan",
    "C42": "lightgray",
    "C43": "lightgoldenrodyellow",
    "C44": "lightskyblue",
    "C45": "lightseagreen",
    "C46": "mediumpurple",
    "C47": "mediumaquamarine",
    "JP4": "mediumorchid",
    "JP5": "mediumslateblue",
    "JP6": "mediumspringgreen",
    "C48": "midnightblue",
    "C49": "mintcream",
    "C50": "moccasin",
    "C51": "navajowhite",
    "C52": "oldlace",
    "C53": "orangered",
    "C54": "palegreen",
}

    print(f"Drawing box with SKU: {box.sku}")
    color = sku_colors.get(box.sku, "gray")  # ใช้สีเทาเป็นค่าเริ่มต้นหาก SKU ไม่อยู่ใน dictionary
    for f in faces:
            poly = Poly3DCollection([vertices[f]], alpha=1.0, facecolor=color, edgecolor='black', linewidth=1.5)
            ax.add_collection3d(poly)

def place_box_in_container(container: Container, box: Box) -> str:
    candidate_positions = container.generate_candidate_positions()
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed"
    return reason

def main():
    df = pd.read_csv("D:/forimport.csv")

    container_length = int(input("Enter container length (mm): "))
    container_width = int(input("Enter container width (mm): "))
    container_height = int(input("Enter container height (mm): "))

    pallet = Pallet(width=1100, length=1100, height=140)
    container = Container(container_length, container_width, container_height, 'blue', pallet)

    boxes_to_place = []
    for index, row in df.iterrows():
        box = Box(length=row['Length'], width=row['Width'], height=row['Height'], sku=row['BoxTypes'], priority=row['Priority'])
        boxes_to_place.append(box)

    start_time = time.time()
    print("\nProcess: Starting box placement.")
    placed_count = 0
    failed_boxes = []
    placed_boxes_info = []

    for i, box in enumerate(boxes_to_place):
        result = place_box_in_container(container, box)
        if result == "Placed":
            placed_count += 1
            print(f"Box {i+1} (SKU: {box.sku}) placed at x={box.x}, y={box.y}, z={box.z}")
            placed_boxes_info.append([box.sku, box.length, box.width, box.height, box.priority, 
                                      round(box.x / 10, 2), round(box.y / 10, 2), round(box.z / 10, 2)])
        else:
            failed_boxes.append([box.sku, box.length, box.width, box.height, box.priority, result])
            print(f"Box {i+1} (SKU: {box.sku}) could not be placed: {result}")

    end_time = time.time()
    print("\nPlacement Summary:")
    print(f" 📊  Total boxes: {len(boxes_to_place)}")
    print(f" ✅  Placed boxes: {placed_count}")
    print(f" ❌ Failed to place: {len(failed_boxes)}")
    for box_info in failed_boxes:
        print(f"  🚫   SKU: {box_info[0]} failed due to: {box_info[-1]}")

    print("\nExporting results to CSV...")

    placed_df = pd.DataFrame(placed_boxes_info, columns=['SKU', 'Length', 'Width', 'Height', 'Priority', 'X (cm)', 'Y (cm)', 'Z (cm)'])
    placed_df.to_csv("PlacedBox.csv", index=False)

    failed_df = pd.DataFrame(failed_boxes, columns=['SKU', 'Length', 'Width', 'Height', 'Priority', 'Reason'])
    failed_df.to_csv("Free_Roller_Boxes.csv", index=False)

    print("\nProcess: Starting visualization.")
    draw_3d_boxes(container)

if __name__ == "__main__":
    main()
