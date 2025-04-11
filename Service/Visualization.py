import configparser
import os
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from Models.Box import Box
from Models.Container import Container

# โหลดค่า BoxColors จาก config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path)

def draw_3d_boxes(container: Container, ax):
    """Draw all boxes in the container in 3D."""
    ax.clear()
    container.pallet.draw_pallet_frame(ax)
    draw_container(ax, container)
    for box in container.boxes:
        draw_box(ax, box)
    ax.set_xlim([0, container.pallet.width])
    ax.set_ylim([0, container.pallet.length])
    ax.set_zlim([0, container.total_height])

    ax.set_xlabel("X (Width mm)")
    ax.set_ylabel("Y (Length mm)")
    ax.set_zlabel("Z (Height mm)")
    
def draw_3d_boxes_with_summary(container: Container, utilization: float, ax):
    draw_3d_boxes(container, ax)
    ax.text2D(
        0.5,
        1.05,
        f"Utilization: {utilization:.2f}%",
        transform=ax.transAxes,
        fontsize=12,
        color="black",
    )
    ax.text2D(
        0.5,
        1.00,
        f"Total Boxes Placed: {len(container.boxes)}",
        transform=ax.transAxes,
        fontsize=12,
        color="black",
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
            linewidths=1,
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
            [vertices[f]], alpha=1.0, facecolor=color, edgecolor="black", linewidth=1.5
        )
        ax.add_collection3d(poly)


def place_box_in_container(container: Container, box: Box):
    """Attempt to place a box in the container."""
    candidate_positions = container.generate_candidate_positions()

    # จัดลำดับตำแหน่งให้เลือก Z ต่ำที่สุดก่อน
    candidate_positions = sorted(candidate_positions, key=lambda pos: (pos[2], pos[1], pos[0]))

    # Try placing the box without rotation
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 1  # No rotation

    # Try placing the box with rotation (swap length and width)
    box.length, box.width = box.width, box.length
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 0  # Rotated

    # Restore original dimensions if placement fails
    box.length, box.width = box.width, box.length
    return "Placement failed", -1  # Placement failed