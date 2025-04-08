import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from Models.Box import Box
from Models.Container import Container

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
    # กำหนดสีตาม SKU
    sku_colors = {
        "C1": "red",
        "C2": "green",
        "C3": "blue",
        "C4": "yellow",
        "C5": "orange",
        "C6": "purple",
        "C7": "cyan",
        "C8": "magenta",
        "C9": "lime",
        "C10": "teal",
        "C11": "maroon",
        "C12": "navy",
        "C13": "olive",
        "C14": "silver",
        "C15": "gold",
        "C16": "coral",
        "C17": "indigo",
        "C18": "violet",
        "C19": "turquoise",
        "C20": "pink",
        "C21": "brown",
        "C22": "aquamarine",
        "C23": "chartreuse",
        "C24": "khaki",
        "C25": "lavender",
        "C26": "salmon",
        "C27": "tan",
        "C28": "plum",
        "C29": "beige",
        "C30": "crimson",
        "C31": "darkgreen",
        "C32": "darkblue",
        "C33": "darkred",
        "C34": "darkorange",
        "C35": "darkcyan",
        "C36": "darkmagenta",
        "C37": "darkkhaki",
        "JP1": "lightcoral",
        "JP2": "lightgreen",
        "JP3": "lightblue",
        "C38": "lightyellow",
        "C39": "lightsalmon",
        "C40": "lightpink",
        "C41": "lightcyan",
        "C42": "lightgray",
        "C43": "lightgoldenrodyellow",
        "C44": "lightskyblue",
        "C45": "lightseagreen",
        "C46": "mediumpurple",
        "C47": "mediumaquamarine",
        "JP4": "mediumorchid",
        "JP5": "mediumslateblue",
        "JP6": "mediumspringgreen",
        "C48": "midnightblue",
        "C49": "mintcream",
        "C50": "moccasin",
        "C51": "navajowhite",
        "C52": "oldlace",
        "C53": "orangered",
        "C54": "palegreen",
    }
    color = sku_colors.get(
        box.sku, "gray"
    )  # ใช้สีเทาเป็นค่าเริ่มต้นหาก SKU ไม่อยู่ใน dictionary
    for f in faces:
        poly = Poly3DCollection(
            [vertices[f]], alpha=1.0, facecolor=color, edgecolor="black", linewidth=1.5
        )
        ax.add_collection3d(poly)

def place_box_in_container(container: Container, box: Box):
    """Attempt to place a box in the container."""
    candidate_positions = container.generate_candidate_positions()

    # Try placing the box without rotation
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 0  # No rotation

    # Try placing the box with rotation (swap length and width)
    box.length, box.width = box.width, box.length
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 1  # Rotated

    # Restore original dimensions if placement fails
    box.length, box.width = box.width, box.length
    return reason, -1  # Placement failed