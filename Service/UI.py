import tkinter as tk
from tkinter import ttk 
from threading import Thread
import configparser
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from Models.Pallet import Pallet
from Models.Box import Box
from Models.Container import Container
import matplotlib.pyplot as plt
import matplotlib

import pandas as pd 
from Service.DataHandler import load_csvFile, export_results
from Service.config_manager import load_config
import os
import logging
import time
import tkinter.simpledialog as simpledialog
from Service.Visualization import draw_3d_boxes_with_summary, place_box_in_container, draw_box

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
        logging.info(f"Matplotlib backend: {matplotlib.get_backend()}")
        config, _ = load_config()
        if not matplotlib.get_backend().lower().startswith("tkagg"):
            logging.warning("⚠️ Current Matplotlib backend may not support GUI rendering properly.")

        master.bind_all('<Control-q>', lambda e: self.on_closing())  # Ctrl+Q เพื่อปิดโปรแกรม
        self.step_index = 0  
        master.bind('<Control-Right>', lambda e: self.show_step_box(forward=True))
        master.bind('<Control-Left>', lambda e: self.show_step_box(forward=False))
        master.bind_all('<Control-k>', lambda e: (print("CTRL+1 triggered"), self.set_mode("op1")))
        master.bind_all('<Control-l>', lambda e: (print("CTRL+2 triggered"), self.set_mode("op2")))
        # โหลด base_dir จาก config.ini
        config, _ = load_config()
        self.base_dir = config.get("Paths", "base_dir")
        default_mode = config.get("AppSettings", "default_mode", fallback="op1")  # โหลดจาก config.ini
        self.mode_var = tk.StringVar(value=default_mode)  # ตั้งค่าจากไฟล์แทนการ hardcode

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
        master.rowconfigure(0, weight=0)   # Toolbar
        master.rowconfigure(1, weight=3)   # Input Settings (30%)
        master.rowconfigure(2, weight=7)   # Summary (70%)
        
        self.container_length = tk.IntVar()
        self.container_width = tk.IntVar()
        self.container_height = tk.IntVar()
        
        self.boxes_to_place = []
        self.container = None
        P_Width = config.get("Pallet", "P_Width")
        P_Length = config.get("Pallet", "P_Length")
        P_Height = config.get("Pallet", "P_Height")
        print(f"🔁 Pallet dimensions: Width={P_Width}, Length={P_Length}, Height={P_Height}")
        self.pallet = Pallet(width=int(P_Width), length=int(P_Length), height=int(P_Height))  # ใช้ค่าจาก config.ini
        
        # Input Frame
        input_frame = tk.LabelFrame(master, text="Input Settings", padx=10, pady=10)  # ใช้ LabelFrame เพื่อเพิ่มหัวข้อ
        input_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(10,5))

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

                # RadioButton สำหรับเลือก Mode
        mode_frame = tk.Frame(input_frame)
        mode_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

        tk.Label(mode_frame, text="Packing Mode:").pack(side="left", padx=(0, 10))
        tk.Radiobutton(mode_frame, text="OP1", variable=self.mode_var, value="op1").pack(side="left")
        tk.Radiobutton(mode_frame, text="OP2", variable=self.mode_var, value="op2").pack(side="left")

        # Buttons
        button_frame = tk.Frame(input_frame)  # เพิ่ม Frame สำหรับปุ่ม
        button_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        self.load_button = tk.Button(button_frame, text="Load CSV", command=lambda: self.run_full_packing_pipeline(self.mode_var.get()), bg="#f0f0f0")
        # master.bind('<Return>', lambda event: self.load_csv())  # กด Enter เพื่อโหลด CSV
        self.load_button.pack(side="left", fill="x", expand=True, padx=5)
        self.run_button = tk.Button(button_frame, text="Run Packing", command=lambda: Thread(target=self.run_packing_op2).start(), bg="#f0f0f0")
        self.run_button.pack(side="left", fill="x", expand=True, padx=5)
        # self.run_button = tk.Button(button_frame, text="Run Packing op1", command=lambda: Thread(target=self.run_packing_op1).start(), bg="#f0f0f0")
        # self.run_button.pack(side="left", fill="x", expand=True, padx=5)
        # self.run_button = tk.Button(button_frame, text="Run Packing op2", command=lambda: Thread(target=self.run_packing_op2).start(), bg="#f0f0f0")
        # self.run_button.pack(side="left", fill="x", expand=True, padx=5)
        self.export_button = tk.Button(button_frame, text="Export Results", command=self.export_results_btn)
        self.export_button.pack(side="left", fill="x", expand=True, padx=5)
        self.explore_button = tk.Button(button_frame, text="Explore", command=self.open_explorer)
        self.explore_button.pack(side="left", fill="x", expand=True, padx=5)

        # Visualization Frame
        self.visualization_frame = tk.LabelFrame(master, text="3D Visualization", padx=10, pady=10)
        self.visualization_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=30, pady=10)


        # ปรับขนาด Figure ให้สูงเต็มจอ
        logging.info("🧪 Creating matplotlib Figure")
        self.fig = plt.Figure(figsize=(16, 30))
        try:
            if self.fig is not None:
                logging.info(f"Figure DPI: {self.fig.dpi}")
            else:
                logging.warning("⚠️ self.fig is None, skipping DPI logging.")
        except Exception as e:
            logging.error(f"⚠️ Failed to access .dpi from self.fig: {e}")
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.visualization_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        # Summary Frame
        self.summary_frame = tk.LabelFrame(master, text="Summary", padx=10, pady=10)
        self.summary_frame.grid(row=2, column=0, columnspan=1, sticky="nsew", padx=10, pady=(5,10))
        self.summary_text = tk.Text(self.summary_frame, height=10, width=80, font=("Segoe UI", 8))
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        master.bind('<Return>', lambda event: self.run_full_packing_pipeline(self.mode_var.get()))  # โหลด → วาง → แสดงผล
        self.progress = ttk.Progressbar(self.summary_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(5, 0))
        
    def set_mode(self, mode):
        self.mode_var.set(mode)
        self.master.update()  # บังคับอัปเดต
        print(f"🔁 Switched to mode: {mode}")  # Debug
        self.summary_text.insert(tk.END, f"🔁 Mode switched to {mode.upper()}\n")
        self.summary_text.see(tk.END)

    def run_full_packing_pipeline(self,  mode="op1"):
        config, _ = load_config()
        data_path = config.get("Paths", "data_path")
        filepath = os.path.join(data_path, "forimport.csv")
        try:
# ตรวจสอบข้อมูล Container Dimention และ ฺBox To Place หากไม่ถูกต้องให้แสดง error message และหยุดการทำงาน
            container_dimensions, self.boxes_to_place = load_csvFile(filepath)
            if container_dimensions is None or self.boxes_to_place is None:
                return 

            container_width, container_length, container_height = container_dimensions
            self.container_width.set(container_width)
            self.container_length.set(container_length)
            self.container_height.set(container_height)
            self.progress["value"] = 0
            logging.info("🚀 Full auto packing pipeline completed on ENTER.")
            if mode == "op1":
                Thread(target=self.run_packing_op1).start()
            elif mode == "op2":
                Thread(target=self.run_packing_op2).start()
                
        except Exception as e:
            logging.error(f"Error in full packing pipeline: {e}")
            messagebox.showerror("Error", f"Error: {e}")
            
    def show_step_box(self, forward=True):
        if not hasattr(self, "placed_df") or self.placed_df.empty:
            messagebox.showinfo("Info", "No placement data to display.")
            return

        # ✅ แก้ตรงนี้: กรองเฉพาะกล่องที่วางสำเร็จ (Out == 0)
        data = self.placed_df[1:]
        data = data[data["X (mm)"].notna() & data["Y (mm)"].notna() & data["Z (mm)"].notna()].reset_index(drop=True)

        total = len(data)
        if total == 0:
            messagebox.showinfo("Info", "No successfully placed boxes to display.")
            return

        if forward:
            self.step_index += 1
            if self.step_index > total:
                self.step_index = 0  # แสดงว่างเปล่า
        else:
            self.step_index -= 1
            if self.step_index < 0:
                self.step_index = total  # ไปจุดสุดท้าย

        self.ax.clear()
        self.container.pallet.draw_pallet_frame(self.ax)

        if self.step_index == 0:
            self.ax.set_title("No box displayed (reset state)")
        else:
            for j in range(self.step_index):
                row = data.iloc[j]
                x, y, z = row["X (mm)"], row["Y (mm)"], row["Z (mm)"]
                sku = row["SKU"]
                box = next(
                    (b for b in self.container.boxes if b.sku == sku and
                    round(b.x, 2) == x and round(b.y, 2) == y and round(b.z, 2) == z),
                    None
                )
                if box:
                    draw_box(self.ax, box)

            last_row = data.iloc[self.step_index - 1]
            if str(last_row["Out"]).strip() == "1":
                self.ax.set_title(f"⚠ Box over height: SKU={last_row['SKU']}")
            else:
                self.ax.set_title(f"Step {self.step_index}: SKU={last_row['SKU']}")


        self.ax.set_xlim([0, self.container.length])
        self.ax.set_ylim([0, self.container.width])
        self.ax.set_zlim([0, self.container.height + self.pallet.height])
        self.canvas.draw()


    def on_hover(self, event):
        event.widget.config(bg="#d0d0d0")  # Change color on hover

    def on_leave(self, event):
        event.widget.config(bg="#f0f0f0")  # Restore default color

    def calculate_utilization(self, box: Box, container: Container) -> float:
        """คำนวณเปอร์เซ็นต์การใช้พื้นที่ของกล่องในคอนเทนเนอร์."""
        box_volume = box.length * box.width * box.height
        container_volume = container.length * container.width * container.height
        return (box_volume / container_volume) * 100 if container_volume > 0 else 0.0
    
    def export_results_btn(self):
        """Export results using data_path from config.ini."""
        if hasattr(self, "placed_df") and not self.placed_df.empty:
            export_results(self.placed_df)
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
            
    def run_packing_op1(self):
        try:
            total_boxes = len(self.boxes_to_place)
            self.progress["maximum"] = total_boxes
            self.progress["value"] = 0
            self.master.update_idletasks()
# แปลงค่าจาก str เป็น int และตรวจสอบความถูกต้อง
# ถ้าไม่มี Container Dimension จะแสดง error message Container dimensions must be valid numbers.
            try:
                container_length = int(self.container_length.get())
                container_width = int(self.container_width.get())
                container_height = int(self.container_height.get())
            except ValueError:
                logging.error("Container dimensions must be valid numbers.")
                messagebox.showerror("Error", "Container dimensions must be valid numbers.")
                return

# ตรวจสอบว่าค่าที่ป้อนเป็นตัวเลขบวกและไม่เป็น 0
            if container_length <= 0 or container_width <= 0 or container_height <= 0:
                logging.error("Container dimensions must be positive numbers and greater than 0.")
                messagebox.showerror("Error", "Container dimensions must be positive numbers and greater than 0.")
                return
# ตรวจสอบว่า box_to_place มีข้อมูลหรือไม่ ในกรณีที่ยังไม่ได้โหลด CSV หรือกดปุ่ม Run Packing ก่อน Load CSV
# ถ้า box_to_place ไม่มีข้อมูลจะแสดง error message Please load a CSV file first.
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
            
# เริ่มคำนวนหาพื้นที่วางกล่องใน Container
            self.summary_text.insert(tk.END, "Process : Starting box placement.\n")
            placed_count = 0
            failed_boxes = []
            placed_boxes_info = []
            placed_volume = 0
            
# วนลูปวางกล่องใน Container
            for i, box in enumerate(self.boxes_to_place):
                self.progress["value"] = i + 1
                self.master.update_idletasks()
                form_conveyor = box.extra_fields.get("cv", "") if hasattr(box, "extra_fields") else ""
                result = place_box_in_container(self.container, box, optional_check="op1")
                # out = 1 if result["exceeds_end_z"] else (0 if result["status"] == "Confirmed" else 1)
                logging.info(f"[OP1]📦 Result for {box.sku}: {result['status']} | R={result['rotation']} | Exceeds height? {result.get('exceeds_end_z', False)} | Reason: {result['message']}")
                out = 0
                cube_utilization = 0
                if result["status"] == "Confirmed":
                    # answer = messagebox.askyesno(
                    #     "Box placement",
                    #     f"Box {box.sku} is within container height.\nDo you want to Confirm placement?",
                    #     icon="question"
                    # )
                    cube_utilization = self.calculate_utilization(box, self.container) if result["status"] == "Confirmed" else 0
                    placed_count += 1
                    placed_volume += box.get_volume()
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku})\nplaced at x={box.x}, y={box.y}, z={box.z} \nwith Rotation={result['rotation']} | Reason: {result['message']}\n",
                    )
                    logging.info(f"[OP1]✅ Confirmed placement for {box.sku} at ({box.x},{box.y},{box.z})")
                elif result["status"] == "Failed":
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku}) could not be placed: {result['message']}\n",
                    )
                    logging.info(f"[OP1]✅ Confirmed placement for {box.sku} at ({box.x},{box.y},{box.z})")
                    logging.warning(f"[OP1]❌ Failed to place {box.sku}: {result['message']}")
                    failed_boxes.append([box.sku, result["message"]])
                    
                elif result["status"] == "OutOfContainer":
                    placed_count += 1
                    placed_volume += box.get_volume()
                    out = 0 
                    cube_utilization = self.calculate_utilization(box, self.container)

                    self.summary_text.insert(
                        tk.END,
                        f"⚠ Box {i+1} (SKU: {box.sku}) placed OUTSIDE container height!\n"
                        f"Position: x={box.x}, y={box.y}, z={box.z} | Rotation={result['rotation']}\n"
                        f"Reason: {result['message']}\n"
                    )
                    logging.warning(f"[OP1]⚠ Placed {box.sku} outside container height at ({box.x},{box.y},{box.z})")

                x = round(box.x, 2)
                y = round(box.y, 2)
                z = round(box.z, 2)
                placed_boxes_info.append([
                    box.sku, 
                    y,
                    x,
                    z,
                    str(result["rotation"]),
                    round(cube_utilization, 2),
                    0,
                    str(box.priority),
                    str(form_conveyor),
                    str(out)
                ])

            end_time = time.time()
# คำนวน utilization ของ Container
            container_volume = (
                self.container.length * self.container.width * self.container.height
            )
            utilization = (placed_volume / container_volume) * 100
# แสดงผลสรุปการวางกล่องใน Container
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
            logging.info(f"[OP1]📋 Creating placed_df with {len(placed_boxes_info)} rows")
# เพิ่ม "Truck #1" เป็นแถวแรกใน placed_boxes_info
            placed_boxes_info.insert(
                0,
                ["Truck #1", "", "", "", "", "", "", "", "", ""]
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
                    "CV",
                    "Out"
                ],
            )

# แสดงกราฟ 3D ของกล่องใน Container พร้อมสรุป
            self.progress["value"] = 0
            draw_3d_boxes_with_summary(self.container, utilization, self.ax)
            self.canvas.draw()
            # ✅ รีเซต step index
            self.step_index = 0
            logging.info("[OP1] Packing process completed successfully.")
            logging.info("[OP1]💾 Starting export_results...")
            self.export_results_btn()
            # Export results automatically
# Exception handling 
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            logging.error(f"[OP1] An error occurred: {e}")

    def run_packing_op2(self):
        try:
            total_boxes = len(self.boxes_to_place)
            self.progress["maximum"] = total_boxes
            self.progress["value"] = 0
            self.master.update_idletasks()

            try:
                container_length = int(self.container_length.get())
                container_width = int(self.container_width.get())
                container_height = int(self.container_height.get())
            except ValueError:
                messagebox.showerror("Error", "Container dimensions must be valid numbers.")
                return

            if container_length <= 0 or container_width <= 0 or container_height <= 0:
                messagebox.showerror("Error", "Container dimensions must be positive numbers and greater than 0.")
                return

            if not self.boxes_to_place:
                messagebox.showerror("Error", "Please load a CSV file first.")
                logging.error("Please load a CSV file first.")
                return

            priorities = [box.priority for box in self.boxes_to_place]
            if priorities != sorted(priorities):
                self.summary_text.insert(
                    tk.END,
                    "⚠ Warning: Priorities are not sequential. Proceeding with the given priorities.\n"
                )
                logging.warning("Priorities are not sequential. Proceeding with the given priorities.")

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
            self.summary_text.insert(tk.END, "Process : Starting box placement (OP2 mode).\n")

            placed_boxes_info = []
            failed_boxes = []
            placed_volume = 0
            placed_count = 0

            for i, box in enumerate(self.boxes_to_place):
                self.progress["value"] = i + 1
                self.master.update_idletasks()
                form_conveyor = box.extra_fields.get("cv", "") if hasattr(box, "extra_fields") else ""
                result = place_box_in_container(self.container, box, optional_check="op2")
                logging.info(f"[OP2]📦 Result for {box.sku}: {result['status']} | R={result['rotation']} | Exceeds height? {result.get('exceeds_end_z', False)} | Reason: {result['message']}")

                out = 1 if result["exceeds_end_z"] else (0 if result["status"] == "Confirmed" else 1)
                cube_utilization = 0
                x = ""
                y = ""
                z = ""
                percent_cube = 0
                print(result["status"])
                if result["status"] == "Confirmed":
                    cube_utilization = self.calculate_utilization(box, self.container) if result["status"] == "Confirmed" else 0
                    placed_count += 1
                    placed_volume += box.get_volume()
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku})\nplaced at x={box.x}, y={box.y}, z={box.z} \nwith Rotation={result['rotation']} | Reason: {result['message']}\n",
                    )
                    
                    x = round(box.x, 2)
                    y = round(box.y, 2)
                    z = round(box.z, 2)
                    percent_cube = round(cube_utilization, 2)
                    logging.info(f"[OP2]✅ Confirmed placement for {box.sku} at ({box.x},{box.y},{box.z})")
                elif result["status"] == "Failed":
                    logging.info(f"[OP2]📦 Result for {box.sku}: {result['status']} | R={result['rotation']} | Exceeds height? {result.get('exceeds_end_z', False)} | Reason: {result['message']}")
                    self.summary_text.insert(
                        tk.END,
                        f"Box {i+1} (SKU: {box.sku}) could not be placed: {result['message']}\n",
                    )
                    logging.info(f"[OP2]✅ Confirmed placement for {box.sku} at ({box.x},{box.y},{box.z})")
                    logging.warning(f"[OP2]❌ Failed to place {box.sku}: {result['message']}")
                    failed_boxes.append([box.sku, result["message"]])
                
                placed_boxes_info.append([
                    box.sku, 
                    y,
                    x,
                    z,
                    str(result["rotation"]),
                    percent_cube,
                    0,
                    str(box.priority),
                    str(form_conveyor), # เพิ่มแก้ไขถ้า CV = "" จะได้ค่าเป็น 0
                    str(out)
                ])

            end_time = time.time()
# คำนวน utilization ของ Container
            container_volume = (
                self.container.length * self.container.width * self.container.height
            )
            utilization = (placed_volume / container_volume) * 100
# แสดงผลสรุปการวางกล่องใน Container
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
            logging.info(f"[OP2]📋 Creating placed_df with {len(placed_boxes_info)} rows")
# เพิ่ม "Truck #1" เป็นแถวแรกใน placed_boxes_info
            placed_boxes_info.insert(
                0,
                ["Truck #1", "", "", "", "", "", "", "", "", ""]
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
                    "CV",
                    "Out"
                ],
            )

# แสดงกราฟ 3D ของกล่องใน Container พร้อมสรุป
            self.progress["value"] = 0
            draw_3d_boxes_with_summary(self.container, utilization, self.ax)
            self.canvas.draw()
            # ✅ รีเซต step index
            self.step_index = 0
            logging.info("[OP2] Packing process completed successfully.")
            logging.info("[OP2]💾 Starting export_results...")
            self.export_results_btn()
            # Export results automatically
# Exception handling 
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            logging.error(f"An error occurred: {e}")
