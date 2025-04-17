import configparser
import os
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from Models.Box import Box
from Models.Container import Container
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from typing import List
import logging

# โหลดค่า BoxColors จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)
# โหลดค่า Support Priority Levels จาก config.ini
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)

# โหลดค่าต่ำสุดของ Support Ratio
min_support_ratio = float(config.get("Container", "required_support_ratio", fallback="0.8"))
GAP = float(config.get("Container", "gap", fallback="5"))  # mm
# โหลด Support Priority Levels และเพิ่มค่าต่ำสุด
support_priority_levels = [
    float(level.strip()) for level in config.get("Container", "support_priority_levels", fallback="1.0, 0.95, 0.9, 0.85").split(",")
]
support_priority_levels.append(min_support_ratio)
support_priority_levels = sorted(support_priority_levels, reverse=True)  # เรียงจากมากไปน้อย

def draw_3d_boxes(container: Container, ax):
    """Draw all boxes in the container in 3D."""
    
    ax.clear()
    
    container.pallet.draw_pallet_frame(ax)
    draw_container(ax, container)
    for box in container.boxes:
        draw_box(ax, box)
    
        # ปรับแต่งกรอบของ Axes
    for spine in ax.spines.values():
        spine.set_edgecolor("red")  # สีของกรอบ
        spine.set_linewidth(5)   
        
    ax.auto_scale_xyz(
        [0, container.pallet.width],
        [0, container.pallet.length],
        [0, container.total_height]
    )
    # ปรับขนาดฟอนต์ของแกน
    ax.tick_params(axis='x',labelsize=8)
    ax.tick_params(axis='y',labelsize=8)
    ax.tick_params(axis='z',labelsize=8)

    ax.set_xlabel("X (Width mm)",fontsize=8)
    ax.set_ylabel("Y (Length mm)",fontsize=8)
    ax.set_zlabel("Z (Height mm)",fontsize=8)

def draw_3d_boxes_with_summary(container: Container, utilization: float, ax):
    draw_3d_boxes(container, ax)

    # เพิ่มข้อความสรุปด้านบนของกราฟ
    ax.text2D(
        0.5,
        1.05,
        f"Utilization: {utilization:.2f}%",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha='center'
    )
    ax.text2D(
        0.5,
        1.00,
        f"Total Boxes Placed: {len(container.boxes)}",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha='center'
    )

    # สร้าง Legend สำหรับแสดง SKU และสี
    legend_elements = {}
    for box in container.boxes:
        if box.sku not in legend_elements:
            color = config.get("BoxColors", box.sku, fallback="gray")
            legend_elements[box.sku] = Patch(facecolor=color, edgecolor='black', label=f"SKU: {box.sku}")

    ax.legend(
        handles=list(legend_elements.values()),
        loc='upper left',
        bbox_to_anchor=(-0.3, 1.05),  # ยึดมุมซ้ายบนของกราฟ
        fontsize=8,
        title="BoxTypes"
    )
    



    
def draw_container(ax, container: Container):
    """Draw the container frame in 3D."""
    x, y, z = container.start_x, container.start_y, container.pallet_height
    dx, dy, dz = container.length, container.width, container.height
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
    faces = [
        [0, 1, 2, 3],  # Bottom
        [0, 1, 5, 4],  # Front
        [1, 2, 6, 5],  # Right
        [2, 3, 7, 6],  # Back
        [3, 0, 4, 7],  # Left
    ]
    ax.add_collection3d(
        Poly3DCollection(
            vertices[faces],
            facecolors="blue",
            linestyle="dashed",
            linewidths=0.3,
            edgecolors="black",
            alpha=0.1,
        )
    )

def draw_box(ax, box: Box):
    """Draw a single box in 3D."""
    x, y, z = box.x, box.y, box.z
    dx, dy, dz = box.length, box.width, box.height
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
    faces = [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7],
    ]

    # ดึงค่าสีจาก config.ini
    color = config.get("BoxColors", box.sku, fallback="gray")  # ใช้สีเทาเป็นค่าเริ่มต้นหากไม่มีใน config.ini

    for f in faces:
        poly = Poly3DCollection(
            [vertices[f]], alpha=1.0, facecolor=color, edgecolor="black", linewidth=1
        )
        ax.add_collection3d(poly)

def has_vertical_clearance(box: Box, placed_boxes: List[Box], container_height: int) -> bool:
    """
    ตรวจสอบว่า:
    - ด้านบนของกล่องมีพื้นที่ว่าง 100%.
    - ด้านล่างของกล่องมีพื้นที่รองรับอย่างน้อย 75%.
    """
    # ตรวจสอบพื้นที่ด้านบน
    box_top = box.z + box.height
    for other in placed_boxes:
        if (
            other.z >= box_top and  # กล่องอื่นอยู่ด้านบน
            not (
                box.x + box.length <= other.x or
                box.x >= other.x + other.length or
                box.y + box.width <= other.y or
                box.y >= other.y + other.width
            )
        ):
            return False  # มีการบังด้านบน

    # ตรวจสอบพื้นที่ด้านล่าง
    if not box.is_supported(placed_boxes, container_height):
        return False  # พื้นที่ด้านล่างไม่เพียงพอ

    return True
def calculate_support_ratio(box: Box, placed_boxes: List[Box], pallet_height: int) -> float:
    """
    คำนวณพื้นที่รองรับด้านล่างของกล่อง (support ratio).
    """
    if box.z <= pallet_height:
        return 1.0  # กล่องอยู่บนพาเลท = 100% รองรับ

    support_area = 0
    total_area = box.length * box.width

    for b in placed_boxes:
        if abs(b.z + b.height - box.z) < 1e-6:  # ตรวจสอบว่ากล่องอยู่ด้านล่าง
            overlap_x = max(0, min(box.x + box.length, b.x + b.length) - max(box.x, b.x))
            overlap_y = max(0, min(box.y + box.width, b.y + b.width) - max(box.y, b.y))
            support_area += overlap_x * overlap_y

    return support_area / total_area if total_area > 0 else 0.0

def place_boxes_by_priority(container: Container, boxes: List[Box]):
    """
    เรียงลำดับกล่องตาม Priority ก่อน แล้ววางทีละกล่อง
    """
    sorted_boxes = sorted(boxes, key=lambda b: b.priority)
    for box in sorted_boxes:
        place_box_in_container(container, box)

def place_box_in_container(container: Container, box: Box):
    """
    Hybrid Placement:
    - Try tight fit (Z -> X -> Y) first with strict support_priority_levels
    - Fallback to scoring method only if no position satisfies support threshold
    - Do NOT adjust_to_center_if_low_support if support < 0.9
    - Skip scoring if strict mode already yields a placement
    """
    import logging

    def distance_from_center(x, y):
        center_x = (container.start_x + container.end_x) / 2
        center_y = (container.start_y + container.end_y) / 2
        return ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5

    def count_neighbors(box):
        count = 0
        for other in container.boxes:
            if other == box or abs(other.z - box.z) > 1e-6:
                continue
            dx = abs((box.x + box.length / 2) - (other.x + other.length / 2))
            dy = abs((box.y + box.width / 2) - (other.y + other.width / 2))
            if dx < max(box.length, other.length) and dy < max(box.width, other.width):
                count += 1
        return count

    candidate_positions = sorted(
        container.generate_candidate_positions(),
        key=lambda pos: (pos[2], pos[0], pos[1])  # Z -> X -> Y
    )

    # --- Phase 1: Strict Mode (tight placement)
    for required_support in support_priority_levels:
        for rotation in [False, True]:
            if rotation:
                box.length, box.width = box.width, box.length

            for x, y, z in candidate_positions:
                box.set_position(x, y, z)
                can_place, reason = container.can_place(box, x, y, z)
                if not can_place:
                    continue

                if not has_vertical_clearance(box, container.boxes, container.height):
                    continue

                support_ratio = calculate_support_ratio(box, container.boxes, container.pallet_height)
                if support_ratio >= required_support:
                    box.set_position(x, y, z)
                    container.place_box(box)
                    logging.info(f"✅ Placed (tight) box '{box.sku}' at ({x},{y},{z}) with support {support_ratio:.2f}, rotation: {'Yes' if rotation else 'No'}")
                    return "Placed (tight)", 0 if rotation else 1

            if rotation:
                box.length, box.width = box.width, box.length

    # --- Phase 2: Scoring Fallback ---
    scored_positions = []
    for rotation in [False, True]:
        if rotation:
            box.length, box.width = box.width, box.length

        for x, y, z in candidate_positions:
            box.set_position(x, y, z)
            can_place, reason = container.can_place(box, x, y, z)
            if not can_place:
                continue

            if not has_vertical_clearance(box, container.boxes, container.height):
                continue

            support_ratio = calculate_support_ratio(box, container.boxes, container.pallet_height)
            if support_ratio < min_support_ratio:
                continue

            center_distance = distance_from_center(x, y)
            neighbor_score = count_neighbors(box)
            score = (support_ratio * 2) - (center_distance / 1000) + (neighbor_score * 0.5)
            scored_positions.append((score, x, y, z, rotation, support_ratio))

        if rotation:
            box.length, box.width = box.width, box.length

    if scored_positions:
        best = max(scored_positions, key=lambda item: item[0])
        _, x, y, z, rotation, best_support = best
        if rotation:
            box.length, box.width = box.width, box.length
        box.set_position(x, y, z)
        container.place_box(box)
        logging.info(f"✅ Fallback placed box '{box.sku}' at ({x},{y},{z}) with support {best_support:.2f}, rotation: {'Yes' if rotation else 'No'}")
        return "Placed (fallback)", 0 if rotation else 1

    logging.warning(f"❌ Box '{box.sku}' could not be placed — no valid position found.")
    return "Placement failed: no position valid", -1



def is_stable_platform(box: Box, placed_boxes: List[Box], pallet_height: int) -> bool:
    """
    ตรวจสอบว่า platform ด้านล่างของกล่องนั้นมีความมั่นคงพอ
    """
    if box.z <= pallet_height:
        return True  # อยู่บนพาเลท ถือว่าเสถียร

    stable_blocks = 0
    for other in placed_boxes:
        if abs(other.z + other.height - box.z) < 1e-6:
            overlap_x = max(0, min(box.x + box.length, other.x + other.length) - max(box.x, other.x))
            overlap_y = max(0, min(box.y + box.width, other.y + other.width) - max(box.y, other.y))
            area = overlap_x * overlap_y
            if area > 0:
                stable_blocks += 1

    return stable_blocks >= 1
