import tkinter as tk
import configparser
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from Models.Pallet import Pallet
from Models.Box import Box
from Models.Container import Container
import matplotlib.pyplot as plt
import pandas as pd 
from Service.DataHandler import load_csvFile, export_results
from Service.config_manager import load_config
from Service.Visualization import draw_3d_boxes_with_summary
from Service.Visualization import draw_3d_boxes_with_summary, place_box_in_container
import os
import logging
import time
import tkinter.simpledialog as simpledialog


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
    def __init__(self, master, start_base_dir):
        master.bind('<Return>', lambda event: self.load_csv())  # กด Enter เพื่อโหลด CSV
        master.bind('<Control-q>', lambda event: self.on_closing())  # Ctrl+Q เพื่อปิดโปรแกรม
        # โหลด base_dir จาก config.ini
        config, _ = load_config()
        self.base_dir = config.get("Paths", "base_dir")

        self.master = master
        self.start_base_dir = start_base_dir
        self.is_browse_open = False  # ตัวแปรสถานะสำหรับตรวจสอบการเปิด Browse
        master.title("Eureka Loader Application")

        # เพิ่มการยืนยันก่อนปิดโปรแกรม
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # สร้างเมนู Toolbar
        self.menu = tk.Menu(master)
        master.config(menu=self.menu)

        # เพิ่มเมนู Settings
        settings_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Set Base Directory", command=self.open_settings_window)
        settings_menu.add_command(label="Set Import CSV Path", command=self.set_import_csv_path)

        

        # Configure grid weights for responsiveness
        master.columnconfigure(0, weight=1)  # ซ้าย 1/5
        master.columnconfigure(1, weight=4)  # ขวา 4/5
        master.rowconfigure(0, weight=0)     # Toolbar
        master.rowconfigure(1, weight=1)     # Content

        self.container_length = tk.IntVar()
        self.container_width = tk.IntVar()
        self.container_height = tk.IntVar()
        self.boxes_to_place = []
        self.container = None
        self.pallet = Pallet(width=1100, length=1100, height=140)
        
        # Input Frame
        input_frame = tk.LabelFrame(master, text="Input Settings", padx=10, pady=10)  # ใช้ LabelFrame เพื่อเพิ่มหัวข้อ
        input_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # แสดง Path ปัจจุบันที่หน้าหลัก
        tk.Label(input_frame, text="Current Base Directory:", anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        self.path_label = tk.Label(input_frame, text=self.base_dir, anchor="w", bg="#f0f0f0", relief="sunken")
        self.path_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Container Dimensions
        tk.Label(input_frame, text="Container Length (mm):").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(input_frame, textvariable=self.container_length).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(input_frame, text="Container Width (mm):").grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(input_frame, textvariable=self.container_width).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(input_frame, text="Container Height (mm):").grid(row=3, column=0, sticky="w", pady=5)
        tk.Entry(input_frame, textvariable=self.container_height).grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # Buttons
        button_frame = tk.Frame(input_frame)  # เพิ่ม Frame สำหรับปุ่ม
        button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        self.load_button = tk.Button(button_frame, text="Load CSV", command=self.load_csv, bg="#f0f0f0")
        master.bind('<Return>', lambda event: self.load_csv())  # กด Enter เพื่อโหลด CSV
        self.load_button.pack(side="left", fill="x", expand=True, padx=5)
        self.run_button = tk.Button(button_frame, text="Run Packing", command=self.run_packing)
        self.run_button.pack(side="left", fill="x", expand=True, padx=5)
        self.export_button = tk.Button(button_frame, text="Export Results", command=self.export_results_btn)
        self.export_button.pack(side="left", fill="x", expand=True, padx=5)
        self.explore_button = tk.Button(button_frame, text="Explore", command=self.open_explorer)
        self.explore_button.pack(side="left", fill="x", expand=True, padx=5)

        # Visualization Frame
        self.visualization_frame = tk.LabelFrame(master, text="3D Visualization", padx=10, pady=10)
        self.visualization_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)


        # ปรับขนาด Figure ให้สูงเต็มจอ
        self.fig = plt.Figure(figsize=(14, 20))  # ขนาดกว้าง 14 นิ้ว สูง 20 นิ้ว
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.visualization_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        # Summary Frame
        self.summary_frame = tk.LabelFrame(master, text="Summary", padx=10, pady=10)
        self.summary_frame.grid(row=2, column=0, columnspan=1, sticky="nsew", padx=10, pady=10)
        self.summary_text = tk.Text(self.summary_frame, height=10, width=80)
        self.summary_text.pack(fill=tk.BOTH, expand=True)


    def on_hover(self, event):
        event.widget.config(bg="#d0d0d0")  # Change color on hover

    def on_leave(self, event):
        event.widget.config(bg="#f0f0f0")  # Restore default color

    def load_csv(self):
        """Load CSV file using data_path from config.ini."""
        config, _ = load_config()
        data_path = config.get("Paths", "data_path")
        filepath = os.path.join(data_path, "forimport.csv")

        try:
            container_dimensions, self.boxes_to_place = load_csvFile()
            if container_dimensions is None or self.boxes_to_place is None:
                return

            container_width, container_length, container_height = container_dimensions
            self.container_width.set(container_width)
            self.container_length.set(container_length)
            self.container_height.set(container_height)
            self.run_packing()
            self.export_results_btn()
        except Exception as e:
            logging.error(f"Failed to load CSV: {e}")
            messagebox.showerror("Error", f"Error loading CSV: {e}")
            
    def calculate_utilization(self, box: Box, container: Container) -> float:
        """คำนวณเปอร์เซ็นต์การใช้พื้นที่ของกล่องในคอนเทนเนอร์."""
        box_volume = box.length * box.width * box.height
        container_volume = container.length * container.width * container.height
        return (box_volume / container_volume) * 100 if container_volume > 0 else 0.0
    
    def run_packing(self):
        try:
            # แปลงค่าจาก str เป็น int และตรวจสอบความถูกต้อง
            try:
                container_length = int(self.container_length.get())
                container_width = int(self.container_width.get())
                container_height = int(self.container_height.get())
            except ValueError:
                messagebox.showerror("Error", "Container dimensions must be valid numbers.")
                return

            # ตรวจสอบว่าค่าที่ป้อนเป็นตัวเลขบวกและไม่เป็น 0
            if container_length <= 0 or container_width <= 0 or container_height <= 0:
                messagebox.showerror("Error", "Container dimensions must be positive numbers and greater than 0.")
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
                    cube_utilization = self.calculate_utilization(box, self.container)
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku}) placed at x={box.x}, y={box.y}, z={box.z} with Rotation={rotation}\n"
                    )
                    placed_boxes_info.append([
                        box.sku, 
                        round(box.y, 2),
                        round(box.x, 2),
                        round(box.z, 2),
                        str(rotation),
                        round(cube_utilization, 2),
                        0,
                        str(box.priority)
                    ])

                    # วาดกล่องแบบสะสมแล้ว update กราฟทีละกล่อง
                    draw_3d_boxes_with_summary(self.container, 0, self.ax)
                    self.canvas.draw()
                    self.master.update_idletasks()
                    self.master.update()  # เพิ่มความลื่นไหล
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
                0,
                ["Truck #1", "", "", "", "", "", "", ""]
            )
            

            # สร้าง DataFrame จาก placed_boxes_info
            self.placed_df = pd.DataFrame(
                placed_boxes_info,
                columns=[
                    "SKU",
                    "Y (mm)",
                    "X (mm)",
                    "Z (mm)",
                    "Rotate",
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
            # Export results automatically
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            logging.error(f"An error occurred: {e}")

    def export_results_btn(self):
        """Export results using data_path from config.ini."""
        if hasattr(self, "placed_df") and hasattr(self, "failed_df"):
            export_results(self.placed_df, self.failed_df)
        else:
            messagebox.showwarning("Warning", "No results to export.")

    def open_explorer(self):
        """เปิด base_dir ใน File Explorer"""
        if os.path.exists(self.base_dir):
            os.startfile(self.base_dir)
        else:
            messagebox.showerror("Error", f"Folder not found: {self.base_dir}")

    def update_path_label(self):
        """อัปเดต Path ปัจจุบันในหน้าหลัก"""
        config, _ = load_config()
        self.base_dir = config.get("Paths", "base_dir")
        self.path_label.config(text=self.base_dir)

    def open_settings_window(self):

            new_path = filedialog.askdirectory(initialdir=self.base_dir, title="Select Base Directory")
            if new_path:
                config, _ = load_config()
                config.set("Paths", "base_dir", new_path)
                config_path = os.path.join(os.path.dirname(__file__), "../config.ini")
                with open(config_path, "w", encoding="utf-8") as config_file:
                    config.write(config_file)
                self.update_path_label()
                messagebox.showinfo("Success", f"Base directory updated to: {new_path}")

    def set_base_dir(self):
        """ตั้งค่า Base Directory และอัปเดตใน config.ini"""
        new_base_dir = filedialog.askdirectory(
            initialdir=self.base_dir,
            title="Select Base Directory"
        )
        if new_base_dir:
            config, _ = load_config()
            config.set("Paths", "base_dir", new_base_dir)
            config_path = os.path.join(os.path.dirname(__file__), "../config.ini")
            with open(config_path, "w", encoding="utf-8") as config_file:
                config.write(config_file)
            self.refresh_ui()  # รีเฟรช UI

    def set_import_csv_path(self):
        """ตั้งค่า Default CSV Path โดยเลือกโฟลเดอร์ก่อน แล้วค้นหาไฟล์ forimport.csv ภายในโฟลเดอร์นั้น"""
        new_folder_path = filedialog.askdirectory(
            initialdir=self.base_dir,
            title="Select Folder Containing forimport.csv"
        )
        if new_folder_path:
            # ตรวจสอบว่าไฟล์ forimport.csv มีอยู่ในโฟลเดอร์ที่เลือกหรือไม่
            csv_file_path = os.path.join(new_folder_path, "forimport.csv")
            if os.path.exists(csv_file_path):
                config, _ = load_config()
                config.set("Paths", "data_path", new_folder_path)
                config_path = os.path.join(os.path.dirname(__file__), "../config.ini")
                with open(config_path, "w", encoding="utf-8") as config_file:
                    config.write(config_file)
                self.update_path_label()  # อัปเดต UI
                messagebox.showinfo("Success", f"CSV path updated to: {csv_file_path}")
            else:
                messagebox.showerror("Error", f"forimport.csv not found in the selected folder: {new_folder_path}")

    def refresh_ui(self):
        """รีเฟรชค่าใน UI จาก config.ini"""
        config, _ = load_config()
        self.base_dir = config.get("Paths", "base_dir")
        self.update_path_label()

    def on_closing(self):
        """แสดงข้อความยืนยันก่อนปิดโปรแกรม"""
        if messagebox.askokcancel("Quit", "Do you want to EXIT?"):
            self.master.destroy()