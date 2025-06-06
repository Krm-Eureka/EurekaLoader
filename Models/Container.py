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
config.read(config_path)
GAP = float(config.get("Container", "gap", fallback=5))  # ใช้ค่า fallback เป็น 5 หากไม่มีใน config.ini
TopSafe = float(config.get("Container", "safeTop", fallback=20))
GapForF5 = float(config.get("Container", "F5", fallback=20))

class Container:
    def __init__(self, length: int, width: int, height: int, color: str, pallet: Pallet, ContainerType: str):
        self.length = length
        self.width = width
        self.height = height
        self.pallet = pallet  
        self.pallet_height = pallet.height
        self.boxes = []
        self.start_x = (pallet.width - self.width) / 2
        self.start_y = (pallet.length - self.length) / 2
        self.end_x = self.start_x + self.width
        self.end_y = self.start_y + self.length
        self.total_height = self.height + pallet.height
        self.end_z = self.total_height - TopSafe
        # self.color = color if ContainerType == "1" else ContainerType == "3": "none" else "brown"  # ถ้าเป็น F5 ให้ใช้สีน้ำตาล

        if ContainerType == "1":
            self.color = color
        elif ContainerType == "3":
            self.color = "yellow"
        else:
            self.color = "brown"  # ถ้าเป็น F5 ให้ใช้สีน้ำตาล

        self.Container_Gap = GAP if ContainerType == ("1" ,"3") else GAP + GapForF5
        # self.can_over_end_z

    def can_place(self, box: Box, x: int, y: int, z: int, optional_check: str = "op2") -> Tuple[bool, str]:
        box_end_x = x + box.length
        box_end_y = y + box.width
        box_end_z = z + box.height

        # ตรวจสอบขอบเขต
        out_of_bounds = (
            x < self.start_x + self.Container_Gap or
            y < self.start_y + self.Container_Gap or
            z < self.pallet_height or  # ป้องกันวางต่ำกว่าพาเลท
            box_end_x > self.end_x - self.Container_Gap or
            box_end_y > self.end_y - self.Container_Gap
        )
        if optional_check == "op2":
            out_of_bounds = out_of_bounds or (box_end_z > (self.end_z- self.Container_Gap) )
            if out_of_bounds:
                print(f"[op2 ❌ out_of_bounds] box_end_z={box_end_z:.1f} > end_z={self.end_z:.1f}, pos=({x},{y},{z})")
                return False, "Out of container bounds"
        elif optional_check == "op1":
            if out_of_bounds:
                print(f"❌ Box {box.sku} out of bounds: x={x}, y={y}, z={z}, end_z={box_end_z}")
                return False, "Out of container bounds"

        # ตรวจสอบการชนกัน (set ตำแหน่งชั่วคราว, เรียก collides_with, แล้ว set กลับตำแหน่งเดิม)
        old_pos = (box.x, box.y, box.z)
        for placed in self.boxes:
            box.set_position(x, y, z)
            collision = box.collides_with(placed)
            box.set_position(*old_pos)
            if collision:
                print(f"[❌ Collision] {box.sku} at ({x},{y},{z}) collides with {placed.sku} at ({placed.x},{placed.y},{placed.z})")
                return False, "Collision with another box"

        # ตรวจสอบการรองรับ (set ตำแหน่งชั่วคราวเพื่อเช็ค support แล้ว set กลับ)
        box.set_position(x, y, z)
        supported = box.is_supported(self.boxes, self.pallet_height)
        box.set_position(*old_pos)
        if not supported:
            return False, "Box not supported from below"

        # ทุกอย่างผ่าน set position จริง
        box.set_position(x, y, z)
                # ✅ เพิ่ม check หากล้นด้านบน เพื่อแสดงใน summary
        # 🔄 ตรวจสอบตามโหมด
        if optional_check == "op2":
            if box_end_z > self.end_z:
                return True, "Exceeds container height (ask user)"
        elif optional_check == "op1":
        # ไม่ตรวจ end_z ใน op1
            pass
        return True, "OK"

    def place_box(self, box: Box):
        self.boxes.append(box)
        
    def generate_candidate_positions(self) -> List[Tuple[int, int, int]]:
        """Generate candidate positions for placing boxes (favoring corners first)."""
        if not self.boxes:
            return [
                (
                    int(self.start_x) + int(self.Container_Gap),
                    int(self.start_y) + int(self.Container_Gap),
                    self.pallet_height,
                )
            ]
        print(f"📍Generating candidate positions, box count = {len(self.boxes)}")       
        positions = set()
        for b in self.boxes:
            for dx in [0, b.length]:
                for dy in [0, b.width]:
                    for dz in [0, b.height]:
                        x, y, z = b.x + dx, b.y + dy, b.z + dz
                        if (
                            self.start_x <= x < self.end_x
                            and self.start_y <= y < self.end_y
                            # and 0 <= z <= self.end_z
                        ):
                            # print(f"🎯 Candidate: x={x}, y={y}, z={z}")  # ✅ Debug ตำแหน่ง
                            positions.add((int(x), int(y), int(z)))

        def min_distance_to_corner(x, y):
            # ใช้ตำแหน่งมุมแบบหัก GAP เพื่อหลีกเลี่ยงเลยขอบ
            corners = [
                (self.start_x, self.start_y),
                (self.end_x - self.Container_Gap, self.start_y),
                (self.start_x, self.end_y - self.Container_Gap),
                (self.end_x - self.Container_Gap, self.end_y - self.Container_Gap),
            ]
            return min(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for cx, cy in corners)

        return sorted(
            positions,
            key=lambda pos: (pos[2], min_distance_to_corner(pos[0], pos[1]))
        )

    # def check_all_collisions(self):
    #     """ตรวจสอบว่ากล่องที่วางทั้งหมดไม่มีการชนกันเลย และ mark กล่องที่ซ้อนทับให้ is_collided=True"""
    #     # เคลียร์ flag ก่อน
    #     for b in self.boxes:
    #         b.is_collided = False
    #     collision_found = False
    #     for i, box1 in enumerate(self.boxes):
    #         for box2 in self.boxes[i+1:]:
    #             if box1.collides_with(box2):
    #                 box1.is_collided = True
    #                 box2.is_collided = True
    #                 print(f"❌ Collision: {box1.sku} at ({box1.x},{box1.y},{box1.z}) overlaps {box2.sku} at ({box2.x},{box2.y},{box2.z})")
    #                 collision_found = True
    #     if not collision_found:
    #         print("✅ No collisions detected among placed boxes.")
    #     return not collision_found




