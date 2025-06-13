import configparser
import os
import math
from typing import List
from tkinter import messagebox, filedialog

# โหลดค่า `required_support_ratio` จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)
REQUIRED_SUPPORT_RATIO = float(config.get("Container", "required_support_ratio", fallback=0.8))  # ค่า fallback เป็น 0.8
BOX_MARGIN = int(config.get("Box","BoxMargin",fallback=7))
class Box:
    def __init__(self, length: int, width: int, height: int, sku: str, priority: int, cv: str, wgt: float, **extra_fields):
        self.x = self.y = self.z = 0
        self.length = length + BOX_MARGIN
        self.width = width + BOX_MARGIN
        self.height = height
        self.sku = sku
        self.priority = priority
        self.cv = str(cv).strip()
        try:
            val = float(wgt)
            self.wgt = 0.0 if math.isnan(val) else val
        except (ValueError, TypeError):
            self.wgt = 0.0

        # เก็บ field เสริมไว้ใน dict
        self.extra_fields = {k.lower(): v for k, v in extra_fields.items()}
        self.is_collided = False  # สำหรับแสดงผลชนกัน

    def set_position(self, x: int, y: int, z: int):
        self.x, self.y, self.z = x, y, z

    def get_volume(self):
        return  self.width * self.length * self.height

    def collides_with(self, other) -> bool:
        return not (
            self.x + self.length <= other.x
            or self.x >= other.x + other.length
            or self.y + self.width <= other.y
            or self.y >= other.y + other.width
            or self.z + self.height <= other.z
            or self.z >= other.z + other.height
        )

    def is_supported(self, placed_boxes: List["Box"], pallet_height: int) -> bool:
        """Check if the box is supported from below."""
        if self.z <= pallet_height:
            return True  # กล่องอยู่บนพาเลท

        support_area = 0
        required_support_area = (self.length * self.width) * REQUIRED_SUPPORT_RATIO  # ใช้ค่าจาก config.ini

        for b in placed_boxes:
            if abs(b.z + b.height - self.z) < 1e-6:  # ตรวจสอบว่ากล่องอยู่ด้านล่าง
                overlap_x = max(0, min(self.x + self.length, b.x + b.length) - max(self.x, b.x))
                overlap_y = max(0, min(self.y + self.width, b.y + b.width) - max(self.y, b.y))
                support_area += overlap_x * overlap_y

                if support_area >= required_support_area:
                    return True

        return False  # กล่องไม่ได้รับการรองรับเพียงพอ
    
    def calculate_support_ratio(self, placed_boxes: List["Box"], pallet_height: int) -> float:
        """คำนวณ support ratio ด้านล่างของกล่อง"""
        if self.z <= pallet_height:
            return 1.0  # อยู่บนพาเลท = รองรับ 100%

        support_area = 0
        total_area = self.length * self.width

        for b in placed_boxes:
            if abs(b.z + b.height - self.z) < 1e-6:  # ต้องสัมผัสด้านล่าง
                overlap_x = max(0, min(self.x + self.length, b.x + b.length) - max(self.x, b.x))
                overlap_y = max(0, min(self.y + self.width, b.y + b.width) - max(self.y, b.y))
                support_area += overlap_x * overlap_y

        return support_area / total_area if total_area > 0 else 0.0
