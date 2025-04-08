import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from Models.Pallet import Pallet
from Models.Container import Container
import matplotlib.pyplot as plt
import pandas as pd 
from Service.DataHandler import load_csv, export_results
from Service.Visualization import draw_3d_boxes_with_summary
from Service.Visualization import draw_3d_boxes_with_summary, place_box_in_container
import os
import logging
import time

class TextHandler(logging.Handler):
    """Custom logging handler to redirect logs to a Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        if self.text_widget.winfo_exists():  # ตรวจสอบว่า widget ยังมีอยู่
            msg = self.format(record)
            self.text_widget.config(state="normal")  # เปิดการแก้ไขชั่วคราว
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.config(state="disabled")  # ปิดการแก้ไข
            self.text_widget.see(tk.END)  # เลื่อนข้อความไปที่บรรทัดสุดท้าย


class PackingApp:
    def __init__(self, master, base_dir):
        self.master = master
        self.base_dir = base_dir
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
        tk.Label(input_frame, text="Container Length (mm):").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(input_frame, textvariable=self.container_length).grid(row=0, column=1, sticky="ew", pady=5)
        tk.Label(input_frame, text="Container Width (mm):").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(input_frame, textvariable=self.container_width).grid(row=1, column=1, sticky="ew", pady=5)
        tk.Label(input_frame, text="Container Height (mm):").grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(input_frame, textvariable=self.container_height).grid(row=2, column=1, sticky="ew", pady=5)

        # Buttons
        self.load_button = tk.Button(input_frame, text="Load CSV", command=self.load_csv, bg="#f0f0f0")
        self.load_button.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
        self.run_button = tk.Button(input_frame, text="Run Packing", command=self.run_packing)
        self.run_button.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        self.export_button = tk.Button(input_frame, text="Export Results", command=self.export_results)
        self.export_button.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        self.explore_button = tk.Button(input_frame, text="Explore", command=self.open_explorer)
        self.explore_button.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

        # Visualization Frame
        self.visualization_frame = tk.Frame(master)
        self.visualization_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.fig = plt.Figure(figsize=(5, 5))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.visualization_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Summary Frame
        self.summary_frame = tk.Frame(master)
        self.summary_frame.grid(row=1, column=0, columnspan=1, sticky="nsew", padx=10, pady=10)
        self.summary_text = tk.Text(self.summary_frame, height=10, width=80)
        self.summary_text.pack(fill=tk.BOTH, expand=True)

        # Log Viewer Frame
        self.log_frame = tk.Frame(master)
        self.log_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.log_text = tk.Text(self.log_frame, height=10, width=50, bg="#f9f9f9", state="normal")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Set up logging to the log viewer
        log_handler = TextHandler(self.log_text)
        log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def on_hover(self, event):
        event.widget.config(bg="#d0d0d0")  # Change color on hover

    def on_leave(self, event):
        event.widget.config(bg="#f0f0f0")  # Restore default color

    def load_csv(self):
        filepath = os.path.join(self.base_dir, "Input", "forimport.csv")
        self.boxes_to_place = load_csv(filepath)
        if self.boxes_to_place:  # ตรวจสอบว่ามีข้อมูลกล่องที่โหลดสำเร็จ
            self.run_packing()  # เรียก run_packing ทันทีหลังจากโหลด CSV

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

            # ตรวจสอบว่า Priority เรียงลำดับหรือไม่
            priorities = [box.priority for box in self.boxes_to_place]
            if priorities != sorted(priorities):
                self.summary_text.insert(
                    tk.END,
                    "⚠ Warning: Priorities are not sequential. Proceeding with the given priorities.\n"
                )
                logging.warning("Priorities are not sequential. Proceeding with the given priorities.")

            # จัดเรียงกล่องตาม Priority (จากน้อยไปมาก)
            self.boxes_to_place.sort(key=lambda box: box.priority)

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
                            box.width,
                            box.length,
                            box.height,
                            round(box.x, 2),
                            round(box.y, 2),
                            round(box.z, 2),
                            rotation,
                            0,  # Placeholder สำหรับ % Cube
                            0,  # Placeholder สำหรับ % Wgt
                            box.priority,
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

            # เพิ่ม "Truck #1" เป็นแถวแรกใน placed_boxes_info
            placed_boxes_info.insert(
                0,  # แทรกที่ตำแหน่งแถวแรก
                [
                    "Truck #1",  
                    "",          
                    "",          
                    "",          
                    "",          
                    "",          
                    "",          
                    "",          
                    "",          
                    "",          
                    "",          
                ]
            )

            # สร้าง DataFrame จาก placed_boxes_info
            self.placed_df = pd.DataFrame(
                placed_boxes_info,
                columns=[
                    "SKU",
                    "Width",
                    "Length",
                    "Height",
                    "X (mm)",
                    "Y (mm)",
                    "Z (mm)",
                    "Rotation",
                    "% Cube",
                    "% Wgt",
                    "Priority",
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
            export_results(self.placed_df, self.failed_df, self.base_dir)
        else:
            messagebox.showwarning("Warning", "No results to export.")
            logging.warning("No results to export.")

    def open_explorer(self):
        """Open the base directory in File Explorer."""
        if os.path.exists(self.base_dir):
            os.startfile(self.base_dir)
        else:
            messagebox.showerror("Error", f"Folder not found: {self.base_dir}")