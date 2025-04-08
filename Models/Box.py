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
            return True
        center_x = self.x + self.length / 2
        center_y = self.y + self.width / 2
        for b in placed_boxes:
            if abs(b.z + b.height - self.z) < 1e-6:
                if (
                    b.x <= center_x <= b.x + b.length
                    and b.y <= center_y <= b.y + b.width
                ):
                    return True
        return False