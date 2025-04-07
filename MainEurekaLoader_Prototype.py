import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from typing import List, Tuple
import numpy as np
import time
import os
import csv
import sys
import logging  # Import the logging module
import configparser  # Import the configparser module
# Determine the base directory


# --- Configuration ---
config = configparser.ConfigParser()

# Determine the base directory
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)  # โฟลเดอร์เดียวกับไฟล์ .exe
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))


config_path = os.path.join(base_dir, "config.ini")
config.read(config_path, encoding="utf-8")
# Check if the config file exists
if not os.path.exists(config_path):
    # Create a default config file if it doesn't exist
    with open(config_path, "w", encoding="utf-8") as config_file:
        config.add_section("Paths")
        config.set("Paths", "default_csv_path", "default.csv")
        config.write(config_file)
        print(f"Config file created at {config_path}. Please edit it before running the program.")
        sys.exit(1)


# --- Logging ---
logging.basicConfig(
    filename=os.path.join(base_dir, "appLogging.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
# เพิ่มการแสดง Log ใน Console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

GAP = 0  # mm


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


class Pallet:
    def __init__(self, width, length, height, frame_height=None, gap=0.2):
        self.width = int(width)
        self.length = int(length)
        self.height = int(height)
        self.frame_height = frame_height if frame_height is not None else height
        self.gap = gap
        self.boxes = []
        self.occupancy_grid = np.zeros(
            (self.width, self.length, self.height), dtype=bool
        )

    def draw_pallet_frame(self, ax):
        x, y, z = 0, 0, 0
        dx, dy, dz = self.width, self.length, self.height
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
        edges = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],
            [4, 5],
            [5, 6],
            [6, 7],
            [7, 4],
            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7],
        ]
        ax.add_collection3d(
            Line3DCollection(
                vertices[edges], color="black", linestyle="dashed", linewidth=2
            )
        )


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
        box_end_x = x + box.length
        box_end_y = y + box.width
        box_end_z = z + box.height

        if (
            x < 0
            or y < 0
            or z < 0
            or box_end_x > self.length
            or box_end_y > self.width
            or box_end_z > self.height
        ):
            return False, "Out of container bounds"

        box.set_position(x, y, z)
        for placed in self.boxes:
            if box.collides_with(placed):
                return False, "Collision with another box"

        if not box.is_supported(self.boxes, self.pallet_height):
            return False, "Box not supported from below"

        return True, "OK"

    def place_box(self, box: Box):
        self.boxes.append(box)

    def generate_candidate_positions(self) -> List[Tuple[int, int, int]]:
        if not self.boxes:
            return [
                (
                    int(self.start_x) + int(GAP),
                    int(self.start_y) + int(GAP),
                    self.pallet_height,
                )
            ]

        positions = []
        for b in self.boxes:
            for dx in [0, b.length]:
                for dy in [0, b.width]:
                    for dz in [0, b.height]:
                        x, y, z = b.x + dx, b.y + dy, b.z + dz
                        if (
                            self.start_x <= x < self.end_x
                            and self.start_y <= y < self.end_y
                            and 0 <= z < self.end_z
                        ):
                            positions.append((int(x), int(y), int(z)))
        return sorted(set(positions), key=lambda pos: (pos[2], pos[1], pos[0]))


def draw_3d_boxes(container: Container, ax):
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


def draw_container(ax, container: Container):
    x, y, z = container.start_x, container.start_y, container.pallet_height
    dx, dy, dz = (
        container.length,
        container.width,
        container.height,
    )
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
    # เลือกเฉพาะ 5 ด้าน (ไม่รวมด้านบน)
    faces = [
        [0, 1, 2, 3],  # ด้านล่าง
        [0, 1, 5, 4],  # ด้านหน้า
        [1, 2, 6, 5],  # ด้านขวา
        [2, 3, 7, 6],  # ด้านหลัง
        [3, 0, 4, 7],  # ด้านซ้าย
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


def place_box_in_container(container: Container, box: Box) -> Tuple[str, int]:
    candidate_positions = container.generate_candidate_positions()

    # ตรวจสอบการวางแบบปกติ (ไม่มีการหมุน)
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 0  # ไม่มีการหมุน (Rotation = 0)

    # ตรวจสอบการวางแบบหมุน (สลับ length และ width)
    box.length, box.width = box.width, box.length  # หมุนกล่อง
    for pos in candidate_positions:
        x, y, z = pos
        can_place, reason = container.can_place(box, x, y, z)
        if can_place:
            box.set_position(x, y, z)
            container.place_box(box)
            return "Placed", 1  # มีการหมุน (Rotation = 1)

    # คืนค่าขนาดเดิมหากไม่สามารถวางได้
    box.length, box.width = box.width, box.length
    return reason, -1  # ไม่สามารถวางได้ (Rotation = -1)


class PackingApp:
    def __init__(self, master):
        self.master = master
        master.title("Eureka Loader Application")

        # Configure grid weights for responsiveness
        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=1)
        master.rowconfigure(0, weight=1)
        master.rowconfigure(1, weight=0)

        self.container_length = tk.IntVar()
        self.container_width = tk.IntVar()
        self.container_height = tk.IntVar()
        self.boxes_to_place = []
        self.container = None
        self.pallet = Pallet(width=1100, length=1100, height=140)

        # Input Frame
        input_frame = tk.Frame(master)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Container Dimensions
        tk.Label(input_frame, text="Container Length (mm):").grid(
            row=0, column=0, sticky="w", pady=5
        )
        tk.Entry(input_frame, textvariable=self.container_length).grid(
            row=0, column=1, sticky="ew", pady=5
        )
        tk.Label(input_frame, text="Container Width (mm):").grid(
            row=1, column=0, sticky="w", pady=5
        )
        tk.Entry(input_frame, textvariable=self.container_width).grid(
            row=1, column=1, sticky="ew", pady=5
        )
        tk.Label(input_frame, text="Container Height (mm):").grid(
            row=2, column=0, sticky="w", pady=5
        )
        tk.Entry(input_frame, textvariable=self.container_height).grid(
            row=2, column=1, sticky="ew", pady=5
        )

        # Load CSV Button
        self.load_button = tk.Button(
            input_frame, text="Load CSV", command=self.load_csv, bg="#f0f0f0"
        )  # Set default background color
        self.load_button.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
        self.load_button.bind("<Enter>", self.on_hover)
        self.load_button.bind("<Leave>", self.on_leave)
        # Run Button
        self.run_button = tk.Button(
            input_frame, text="Run Packing", command=self.run_packing
        )
        self.run_button.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        self.run_button.bind("<Enter>", self.on_hover)
        self.run_button.bind("<Leave>", self.on_leave)

        # Export Button
        self.export_button = tk.Button(
            input_frame, text="Export Results", command=self.export_results
        )
        self.export_button.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        self.export_button.bind("<Enter>", self.on_hover)
        self.export_button.bind("<Leave>", self.on_leave)

        # Visualization Frame
        self.visualization_frame = tk.Frame(master)
        self.visualization_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.fig = plt.Figure(figsize=(5, 5))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.visualization_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Summary Frame
        self.summary_frame = tk.Frame(master)
        self.summary_frame.grid(
            row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10
        )
        self.summary_text = tk.Text(self.summary_frame, height=10, width=80)
        self.summary_text.pack(fill=tk.BOTH, expand=True)

    def on_hover(self, event):
        event.widget.config(bg="#d0d0d0")  # Change color on hover

    def on_leave(self, event):
        event.widget.config(bg="#f0f0f0")  # Restore default color

    def load_csv(self):
        try:
            # อ่านค่า default_csv_path จาก config.ini
            default_filepath = config.get("Paths", "default_csv_path")
            if not os.path.isabs(default_filepath):
                # ถ้าเป็น Path แบบ Relative ให้แปลงเป็น Absolute Path
                default_filepath = os.path.join(base_dir, default_filepath)

            logging.info(f"Default file path: {default_filepath}")
            # Check if the default file exists
            if not os.path.exists(default_filepath):
                messagebox.showerror("Error", f"File not found: {default_filepath}")
                logging.error(f"File not found: {default_filepath}")
                return

            # If the default file exists, use it
            filepath = default_filepath
            logging.info(f"Using default file path: {default_filepath}")
            
            if filepath:
                try:
                    df = pd.read_csv(filepath, encoding="utf-8")
                    logging.info(f"Loaded CSV file: {filepath}")
                    if df.empty:
                        messagebox.showerror("Error", "CSV file is empty.")
                        logging.error("CSV file is empty.")
                        return
                    required_columns = ["Length", "Width", "Height", "BoxTypes", "Priority"]
                    for col in required_columns:
                        if col not in df.columns:
                            messagebox.showerror(
                                "Error", f"Missing required column: {col}"
                            )
                            logging.error(f"Missing required column: {col}")
                            return
                    self.boxes_to_place = []
                    for index, row in df.iterrows():
                        box = Box(
                            length=row["Length"],
                            width=row["Width"],
                            height=row["Height"],
                            sku=row["BoxTypes"],
                            priority=row["Priority"],
                        )
                        self.boxes_to_place.append(box)
                    messagebox.showinfo("Success", "CSV loaded successfully!")
                    logging.info("CSV loaded successfully!")
                except pd.errors.EmptyDataError:
                    messagebox.showerror("Error", f"File is empty: {filepath}")
                    logging.error(f"File is empty: {filepath}")
                except pd.errors.ParserError:
                    messagebox.showerror("Error", f"Error parsing CSV file: {filepath}")
                    logging.error(f"Error parsing CSV file: {filepath}")
                except FileNotFoundError:
                    messagebox.showerror("Error", f"File not found: {filepath}")
                    logging.error(f"File not found: {filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Error loading CSV: {e}")
                    logging.error(f"Error loading CSV: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            logging.error(f"An unexpected error occurred: {e}")

    def run_packing(self):
        try:
            container_length = self.container_length.get()
            container_width = self.container_width.get()
            container_height = self.container_height.get()

            if not all([container_length, container_width, container_height]):
                messagebox.showerror("Error", "Please enter container dimensions.")
                logging.error("Please enter container dimensions.")
                return

            if not self.boxes_to_place:
                messagebox.showerror("Error", "Please load a CSV file first.")
                logging.error("Please load a CSV file first.")
                return

            self.container = Container(
                container_length,
                container_width,
                container_height,
                "blue",
                self.pallet,
            )

            start_time = time.time()
            self.summary_text.delete("1.0", tk.END)
            self.summary_text.insert(tk.END, "Process: Starting box placement.\n")
            placed_count = 0
            failed_boxes = []
            placed_boxes_info = []
            placed_volume = 0

            for i, box in enumerate(self.boxes_to_place):
                result, rotation = place_box_in_container(self.container, box)
                if result == "Placed":
                    placed_count += 1
                    placed_volume += box.get_volume()
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku}) placed at x={box.x}, y={box.y}, z={box.z} with Rotation={rotation}\n",
                    )
                    placed_boxes_info.append(
                        [
                            box.sku,
                            box.length,
                            box.width,
                            box.height,
                            box.priority,
                            round(box.x / 10, 2),
                            round(box.y / 10, 2),
                            round(box.z / 10, 2),
                            rotation,
                        ]
                    )
                else:
                    failed_boxes.append(
                        [box.sku, box.length, box.width, box.height, box.priority, result]
                    )
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku}) could not be placed: {result}\n",
                    )

            end_time = time.time()

            container_volume = (
                self.container.length * self.container.width * self.container.height
            )
            utilization = (placed_volume / container_volume) * 100

            self.summary_text.insert(tk.END, "\nPlacement Summary:\n")
            self.summary_text.insert(
                tk.END, f" 📊  Total boxes: {len(self.boxes_to_place)}\n"
            )
            self.summary_text.insert(tk.END, f" ✅  Placed boxes: {placed_count}\n")
            self.summary_text.insert(
                tk.END, f" ❌ Failed to place: {len(failed_boxes)}\n"
            )
            self.summary_text.insert(tk.END, f" 📦 Utilization: {utilization:.2f}%\n")
            for box_info in failed_boxes:
                self.summary_text.insert(
                    tk.END, f"  🚫   SKU: {box_info[0]} failed due to: {box_info[-1]}\n"
                )

            self.placed_df = pd.DataFrame(
                placed_boxes_info,
                columns=[
                    "SKU",
                    "Length",
                    "Width",
                    "Height",
                    "Priority",
                    "X (cm)",
                    "Y (cm)",
                    "Z (cm)",
                    "Rotation",
                ],
            )
            self.failed_df = pd.DataFrame(
                failed_boxes,
                columns=["SKU", "Length", "Width", "Height", "Priority", "Reason"],
            )

            draw_3d_boxes_with_summary(self.container, utilization, self.ax)
            self.canvas.draw()
            logging.info("Packing process completed successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            logging.error(f"An error occurred: {e}")

    def export_results(self):
        if hasattr(self, "placed_df") and hasattr(self, "failed_df"):
            try:
                self.placed_df.to_csv("PlacedBox.csv", index=False)
                self.failed_df.to_csv("Free_Roller_Boxes.csv", index=False)
                messagebox.showinfo("Success", "Results exported to CSV files.")
                logging.info("Results exported to CSV files.")
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting results: {e}")
                logging.error(f"Error exporting results: {e}")
        else:
            messagebox.showwarning("Warning", "No results to export.")
            logging.warning("No results to export.")


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


def main():
    root = tk.Tk()
    app = PackingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
