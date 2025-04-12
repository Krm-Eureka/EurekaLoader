import configparser
import os
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from Models.Box import Box
from Models.Container import Container
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

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

def place_box_in_container(container: Container, box: Box):
    """Attempt to place a box in the container."""
    candidate_positions = container.generate_candidate_positions()

    # จัดลำดับตำแหน่งให้เลือก Z ต่ำที่สุดก่อน
    candidate_positions = sorted(candidate_positions, key=lambda pos: (pos[2], pos[1], pos[0]))

    # Try placing the box without rotation
    for pos in candidate_positions:
        x, y, z = pos
        if x!= 5 and y!= 5:
            x = x + 5
            y = y + 5
            
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 1  # No rotation

    # Try placing the box with rotation (swap length and width)
    box.length, box.width = box.width, box.length
    for pos in candidate_positions:
        x, y, z = pos
        if x!= 5 and y!= 5:
            x = x + 5
            y = y + 5
            
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 0  # Rotated

    # Restore original dimensions if placement fails
    box.length, box.width = box.width, box.length
    return "Placement failed", -1  # Placement failed