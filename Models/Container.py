from typing import List, Tuple
import os
import configparser
from tkinter import messagebox, filedialog
from Models.Box import Box
from Models.Pallet import Pallet
import numpy as np

# โหลดค่า GAP จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path, encoding="utf-8")

TopSafe = float(config.get("Container", "safeTop", fallback=20))
GapForF5 = int(config.get("Container", "F5", fallback=20))
F5_SAFE_END_Y = int(config.get("Container", "F5_SAFE_END_Y", fallback=5))
F5_SAFE_END_X = int(config.get("Container", "F5_SAFE_END_X", fallback=5))
GAP_START_X = int(config.get("Container", "GapStartX", fallback=5))
GAP_END_X = int(config.get("Container", "GapEndX", fallback=5))
GAP_START_Y = int(config.get("Container", "GapStartY", fallback=5))
GAP_END_Y = int(config.get("Container", "GapEndY", fallback=5))

class Container:
    def __init__(self, length: int, width: int, height: int, color: str, pallet: Pallet, ContainerType: str):
        self.length = length
        self.width = width
        self.height = height
        self.pallet = pallet  
        self.pallet_height = pallet.height
        self.boxes = []

        # คัดลอกค่าตั้งต้นจาก config
        self.gap_start_x = GAP_START_X
        self.gap_end_x = GAP_END_X
        self.gap_start_y = GAP_START_Y
        self.gap_end_y = GAP_END_Y

        # ปรับค่าตามประเภท container
        if ContainerType == "1":  # F15
            self.color = color
        elif ContainerType == "3":  # Pallet
            self.color = "yellow"
        else:  # F5
            self.gap_start_x += GapForF5
            self.gap_end_x += GapForF5 + F5_SAFE_END_Y
            self.gap_start_y += GapForF5
            self.gap_end_y += GapForF5 + F5_SAFE_END_X
            self.color = "brown"

        center_x = (pallet.width - self.width) / 2
        center_y = (pallet.length - self.length) / 2

        self.start_x = center_x + self.gap_start_x
        self.end_x = center_x + self.width - self.gap_end_x
        self.start_y = center_y + self.gap_start_y
        self.end_y = center_y + self.length - self.gap_end_y

        self.total_height = self.height + pallet.height
        self.end_z = self.total_height - TopSafe

        # เพิ่ม attributes สำหรับใช้ใน Visualization
        self.container_dx = self.end_x - self.start_x
        self.container_dy = self.end_y - self.start_y

    def can_place(self, box: Box, x: int, y: int, z: int, optional_check: str = "op2") -> Tuple[bool, str]:
        box_end_x = x + box.length
        box_end_y = y + box.width
        box_end_z = z + box.height
        print(f"[DEBUG] \U0001f4e6 SKU={box.sku} | x={x}, y={y}, z={z}")
        print(f"        start_x={self.start_x}, start_y={self.start_y}, end_x={self.end_x}, end_y={self.end_y}")
        print(f"        box_end_z={box_end_z}, end_z={self.end_z}")

        out_of_bounds = (
            x < self.start_x or
            y < self.start_y or
            z < self.pallet_height or
            box_end_x > self.end_x or
            box_end_y > self.end_y
        )
        if optional_check == "op2":
            out_of_bounds = out_of_bounds or (box_end_z > self.end_z)
            if out_of_bounds:
                print(f"[op2 ❌ out_of_bounds] x={x}, y={y}, z={z}, end_y={box_end_y:.1f} > max={self.end_y:.1f}")
                return False, "Out of container bounds"
        elif optional_check == "op1":
            if out_of_bounds:
                print(f"❌ Box {box.sku} out of bounds: x={x}, y={y}, z={z}, end_y={box_end_y:.1f} > max={self.end_y:.1f}")
                return False, "Out of container bounds"

        old_pos = (box.x, box.y, box.z)
        for placed in self.boxes:
            box.set_position(x, y, z)
            if box.collides_with(placed):
                box.set_position(*old_pos)
                print(f"[❌ Collision] {box.sku} at ({x},{y},{z}) collides with {placed.sku} at ({placed.x},{placed.y},{placed.z})")
                return False, "Collision with another box"
        box.set_position(*old_pos)

        box.set_position(x, y, z)
        supported = box.is_supported(self.boxes, self.pallet_height)
        box.set_position(*old_pos)
        if not supported:
            return False, "Box not supported from below"

        box.set_position(x, y, z)
        if optional_check == "op2" and box_end_z > self.end_z:
            return True, "Exceeds container height (ask user)"

        return True, "OK"

    def place_box(self, box: Box):
        self.boxes.append(box)

    def generate_candidate_positions(self) -> List[Tuple[int, int, int]]:
        def distance_to_edge(x: int, y: int) -> float:
            dx = min(x - self.start_x, self.end_x - x)
            dy = min(y - self.start_y, self.end_y - y)
            return min(dx, dy)
        positions = set()

        # 🔰 เพิ่ม corner positions สำหรับวางที่ขอบ container
        positions.update([
            (int(self.start_x), int(self.start_y), self.pallet_height),
            (int(self.end_x - 1), int(self.start_y), self.pallet_height),
            (int(self.start_x), int(self.end_y - 1), self.pallet_height),
            (int(self.end_x - 1), int(self.end_y - 1), self.pallet_height),
        ])

        if not self.boxes:
            return list(positions)

        print(f"\U0001f4cdGenerating candidate positions, box count = {len(self.boxes)}")       
        for b in self.boxes:
            for dx in [0, b.length]:
                for dy in [0, b.width]:
                    for dz in [0, b.height]:
                        x, y, z = b.x + dx, b.y + dy, b.z + dz
                        if (
                            self.start_x <= x < self.end_x and
                            self.start_y <= y < self.end_y
                        ):
                            positions.add((int(x), int(y), int(z)))

        def min_distance_to_corner(x, y):
            corners = [
                (self.start_x, self.start_y),
                (self.end_x, self.start_y),
                (self.start_x, self.end_y),
                (self.end_x, self.end_y),
            ]
            return min(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for cx, cy in corners)
        # return sorted(
        #     positions,
        #     key=lambda pos: (pos[2], distance_to_edge(pos[0], pos[1]), pos[0], pos[1])
        # )
        return sorted(
                        positions,
                        key=lambda pos: (pos[2], pos[0], pos[1])  # Z → X → Y
                    )
