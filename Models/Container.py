from typing import List, Tuple
import os
import configparser
from Models.Box import Box
from Models.Pallet import Pallet
import numpy as np

# โหลดค่า GAP จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)
GAP = float(config.get("Container", "gap", fallback=5))  # ใช้ค่า fallback เป็น 2.5 หากไม่มีใน config.ini

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
        self.total_height = self.height + self.pallet_height
        self.end_z = self.total_height

    def can_place(self, box: Box, x: int, y: int, z: int) -> Tuple[bool, str]:
        """Check if a box can be placed at the given position."""
        box_end_x = x + box.length
        box_end_y = y + box.width
        box_end_z = z + box.height

        if (
                x < self.start_x + GAP
                or y < self.start_y + GAP
                or z < 0
                or x + box.length > self.end_x - GAP
                or y + box.width > self.end_y - GAP
                or z + box.height > self.end_z
            ):
                return False, "Out of container bounds (GAP)"


        box.set_position(x, y, z)

        # ตรวจสอบการชนกัน
        for placed in self.boxes:
            if box.collides_with(placed):
                return False, "Collision with another box"

        # ตรวจสอบการรองรับ
        if not box.is_supported(self.boxes, self.pallet_height):
            return False, "Box not supported from below"

        return True, "OK"

    def place_box(self, box: Box):
        self.boxes.append(box)

    def generate_candidate_positions(self) -> List[Tuple[int, int, int]]:
        """Generate candidate positions for placing boxes (favoring corners first)."""
        if not self.boxes:
            return [
                (
                    int(self.start_x) + int(GAP),
                    int(self.start_y) + int(GAP),
                    self.pallet_height,
                )
            ]

        positions = set()
        for b in self.boxes:
            for dx in [0, b.length]:
                for dy in [0, b.width]:
                    for dz in [0, b.height]:
                        x, y, z = b.x + dx, b.y + dy, b.z + dz
                        if (
                            self.start_x <= x < self.end_x
                            and self.start_y <= y < self.end_y
                            and 0 <= z <= self.end_z
                        ):
                            positions.add((int(x), int(y), int(z)))

        def min_distance_to_corner(x, y):
            # ใช้ตำแหน่งมุมแบบหัก GAP เพื่อหลีกเลี่ยงเลยขอบ
            corners = [
                (self.start_x, self.start_y),
                (self.end_x - GAP, self.start_y),
                (self.start_x, self.end_y - GAP),
                (self.end_x - GAP, self.end_y - GAP),
            ]
            return min(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for cx, cy in corners)

        return sorted(
            positions,
            key=lambda pos: (pos[2], min_distance_to_corner(pos[0], pos[1]))
        )



    
