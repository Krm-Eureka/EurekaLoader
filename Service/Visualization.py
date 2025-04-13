import configparser
import os
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from Models.Box import Box
from Models.Container import Container
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from typing import List

# โหลดค่า BoxColors จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)

# โหลดค่า Support Priority Levels จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)

# โหลดค่าต่ำสุดของ Support Ratio
min_support_ratio = float(config.get("Container", "required_support_ratio", fallback="0.8"))

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

def enable_zoom(ax, canvas=None, max_limits=None):
    """Enable zoom functionality for a 3D plot with boundary constraints."""
    def on_scroll(event):
        """Handle scroll events for zooming."""
        scale_factor = 1.1  # กำหนดอัตราการซูม
        if event.button == 'up':  # Scroll Up -> Zoom In
            new_xlim = [coord / scale_factor for coord in ax.get_xlim()]
            new_ylim = [coord / scale_factor for coord in ax.get_ylim()]
            new_zlim = [coord / scale_factor for coord in ax.get_zlim()]
        elif event.button == 'down':  # Scroll Down -> Zoom Out
            new_xlim = [coord * scale_factor for coord in ax.get_xlim()]
            new_ylim = [coord * scale_factor for coord in ax.get_ylim()]
            new_zlim = [coord * scale_factor for coord in ax.get_zlim()]
        else:
            return

        # ตรวจสอบขอบเขตไม่ให้เกิน max_limits (ถ้ากำหนดไว้)
        if max_limits:
            new_xlim = [
                max(new_xlim[0], max_limits['x'][0]),
                min(new_xlim[1], max_limits['x'][1]),
            ]
            new_ylim = [
                max(new_ylim[0], max_limits['y'][0]),
                min(new_ylim[1], max_limits['y'][1]),
            ]
            new_zlim = [
                max(new_zlim[0], max_limits['z'][0]),
                min(new_zlim[1], max_limits['z'][1]),
            ]

        # อัปเดตขอบเขตแกน
        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        ax.set_zlim(new_zlim)

        # อัปเดตการแสดงผล
        if canvas:
            canvas.draw()  # สำหรับ Tkinter
        else:
            plt.draw()  # สำหรับ Matplotlib ปกติ

    # เชื่อมต่อ Scroll Event กับฟังก์ชัน on_scroll
    ax.figure.canvas.mpl_connect('scroll_event', on_scroll)
    
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
    legend_elements = []
    for box in container.boxes:
        color = config.get("BoxColors", box.sku, fallback="gray")  # ดึงสีจาก config.ini
        if not any(legend.get_label() == f"SKU: {box.sku}" for legend in legend_elements):  # ตรวจสอบไม่ให้ซ้ำ
            legend_elements.append(Patch(facecolor=color, edgecolor='black', label=f"SKU: {box.sku}"))

    # เพิ่ม Legend ในกราฟ
    ax.legend(
        handles=legend_elements,
        loc='upper left',  # ตำแหน่งของ Legend
        bbox_to_anchor=(-0.7,1.05),  # ปรับตำแหน่ง Legend
        fontsize=8,
        title="BoxTypes"
    )

    enable_zoom(ax)  # Enable zoom functionality
    
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

def place_box_in_container(container: Container, box: Box):
    """Attempt to place a box in the container."""
    candidate_positions = container.generate_candidate_positions()
    failure_reason = "No suitable position found."  # เหตุผลเริ่มต้น

    # ลองทั้งแบบไม่หมุน และหมุน
    for rotation in [False, True]:
        if rotation:
            box.length, box.width = box.width, box.length  # หมุนกล่อง

        # เก็บตำแหน่งที่เหมาะสมพร้อม support_ratio
        supportable_positions = []
        for pos in candidate_positions:
            x, y, z = pos
            box.set_position(x, y, z)
            can_place, reason = container.can_place(box, x, y, z)

            if can_place:
                support_ratio = calculate_support_ratio(box, container.boxes, container.pallet_height)
                if not has_vertical_clearance(box, container.boxes, container.height):  # ตรวจสอบ clearance แนวดิ่ง
                    failure_reason = "Vertical clearance not sufficient."
                    continue

                supportable_positions.append((support_ratio, (x, y, z)))

        # เรียงตำแหน่งจาก support สูงสุด → ต่ำสุด
        supportable_positions.sort(reverse=True, key=lambda item: item[0])

        # ลองวางจากลำดับ support_priority_levels
        for required_support in support_priority_levels:
            for support_ratio, (x, y, z) in supportable_positions:
                if support_ratio >= required_support:
                    box.set_position(x, y, z)
                    container.place_box(box)
                    return "Placed", 1 if not rotation else 0

            failure_reason = f"Support ratio below required level ({required_support})."

    # ถ้าไม่มีตำแหน่งที่เหมาะสม
    if rotation:
        box.length, box.width = box.width, box.length  # คืนขนาดเดิม

    return f"Placement failed: {failure_reason}", -1