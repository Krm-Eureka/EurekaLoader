from typing import List

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
            self.x + self.length <= other.x
            or self.x >= other.x + other.length
            or self.y + self.width <= other.y
            or self.y >= other.y + other.width
            or self.z + self.height <= other.z
            or self.z >= other.z + other.height
        )

    def is_supported(self, placed_boxes: List["Box"], pallet_height: int) -> bool:
        if self.z <= pallet_height:
            return True  # กล่องอยู่บนพาเลท

        # คำนวณพื้นที่ที่ต้องการการรองรับ
        support_area = 0
        required_support_area = (self.length * self.width) * 0.6  # ต้องการการรองรับอย่างน้อย 60%

        for b in placed_boxes:
            if abs(b.z + b.height - self.z) < 1e-6:  # ตรวจสอบว่ากล่องอยู่ด้านล่าง
                # คำนวณพื้นที่ที่กล่องด้านล่างรองรับ
                overlap_x = max(0, min(self.x + self.length, b.x + b.length) - max(self.x, b.x))
                overlap_y = max(0, min(self.y + self.width, b.y + b.width) - max(self.y, b.y))
                support_area += overlap_x * overlap_y

                # หากพื้นที่รองรับเพียงพอแล้ว ให้คืนค่า True
                if support_area >= required_support_area:
                    return True

        return False  # กล่องไม่ได้รับการรองรับเพียงพอ