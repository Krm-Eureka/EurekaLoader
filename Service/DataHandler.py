import os
import pandas as pd
import sys
import tkinter as tk
from tkinter import messagebox 
import logging
from Models.Box import Box
from Models.Container import Container
from Service.config_manager import load_config
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def load_csvFile(fileForimportPath: str):
    """Load box data and container dimensions from a CSV file."""
    # config, _ = load_config()
    # data_path = config.get("Paths", "data_path")
    # filepath = os.path.join(data_path, "forimport.csv")

    try:
        logging.info(f"Attempting to load CSV file from: {fileForimportPath}")
        if not os.path.exists(fileForimportPath):
            logging.warning(f"CSV file not found. Creating a sample file at: {fileForimportPath}")
            # Create a sample file if it doesn't exist
            sample_data = (
                "Container,,C_Width,C_Length,C_Height\n"
                "F15,,1060,1060,920\n"
                "Priority,BoxTypes,Width,Length,Height\n"
                "1,TEST1,100,200,150\n"
                "2,TEST2,120,220,160\n"
                "3,TEST3,140,240,170\n"
            )
            with open(fileForimportPath, "w", encoding="utf-8") as f:
                f.write(sample_data)
            messagebox.showinfo("Info", f"Sample file created: {fileForimportPath}. Please edit it and reload.")
            return None, None

        # Load CSV file
        with open(fileForimportPath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            messagebox.showerror("Error", "CSV file is empty.")
            return None, None

        # ----- อ่านข้อมูล Container -----
        container_line_index = next((i for i, line in enumerate(lines) if line.strip().startswith("Container")), None)
        if container_line_index is None or container_line_index + 1 >= len(lines):
            messagebox.showerror("Error", "Container data not found.")
            return None, None

        container_data = lines[container_line_index + 1].strip().split(",")
        if len(container_data) < 5:
            messagebox.showerror("Error", "Invalid container data format.")
            return None, None

        try:
            container_width = int(container_data[2])
            container_length = int(container_data[3])
            container_height = int(container_data[4])
            print(f"Container dimensions: Width={container_width}, Length={container_length}, Height={container_height}")
        except (IndexError, ValueError):
            logging.error("Error parsing container dimensions.")
            messagebox.showerror("Error", "Invalid container dimensions.")
            return None, None

        logging.info(f"Container dimensions loaded: Width={container_width}, Length={container_length}, Height={container_height}")

        # ----- อ่านข้อมูล Box -----
        box_start_index = next((i for i, line in enumerate(lines) if line.strip().startswith("Priority")), None)
        if box_start_index is None:
            messagebox.showerror("Error", "Box data header not found.")
            return None, None

        # อ่านข้อมูลกล่องตั้งแต่แถวที่มี Priority เป็นต้นไป
        temp_path = fileForimportPath + "_temp_box_only.csv"
        with open(temp_path, "w", encoding="utf-8") as temp_f:
            temp_f.writelines(lines[box_start_index:])

        # เพิ่มการตรวจสอบข้อมูลในไฟล์ CSV
        df = pd.read_csv(temp_path, delimiter=",")  # ระบุ delimiter
        logging.info(f"DataFrame loaded: \n{df.to_string()}")
        df.columns = [col.lower() for col in df.columns]  # เปลี่ยนชื่อคอลัมน์เป็นตัวพิมพ์เล็ก
        required_columns = ["priority", "boxtypes", "width", "length", "height"]
        if not all(col in df.columns for col in required_columns):
            missing_columns = [col for col in required_columns if col not in df.columns]
            logging.error(f"CSV file missing required columns: {missing_columns}")
            messagebox.showerror("Error", f"CSV file missing required columns: {missing_columns}")
            return None, None

        boxes_to_place = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            box = Box(
                length=row_dict.pop("length"),
                width=row_dict.pop("width"),
                height=row_dict.pop("height"),
                sku=row_dict.pop("boxtypes"),
                priority=int(row_dict.pop("priority")),
                **row_dict  # ที่เหลือส่งเข้าไปเป็น extra_fields
            )
            print(f"Loaded box: {box.sku}, extras: {box.extra_fields}")
            boxes_to_place.append(box)

        logging.info(f"Loaded {len(boxes_to_place)} boxes from CSV.")

        return (container_width, container_length, container_height), boxes_to_place

    except Exception as e:
        logging.error(f"Error loading CSV: {e}")
        messagebox.showerror("Error", f"Error loading CSV: {e}")
        return None, None

def export_results(placed_df):
    """Export results to CSV files."""
    config, _ = load_config()
    data_path = config.get("Paths", "data_path")
    placed_file_export_path = os.path.join(data_path, "forexport.txt")

    try:
        export_lines = []
        for _, row in placed_df.iterrows():
            out = row.get("Out")
            if pd.notna(out) and str(out).strip() == "0":
                export_lines.append(
                    f"{row['SKU']},{row['Y (mm)']},{row['X (mm)']},{row['Z (mm)']},{row['Rotate']},{row['% Cube']},{row['% Wgt']},{row['Priority']},{row['Out']}"
                )
            else:
                export_lines.append(
                    f"{row['SKU']},,,,,,{row['% Wgt']},{row['Priority']},{row['Out']}"
                )

        # ✅ ย้ายมาไว้ตรงนี้ (นอกลูป)
        with open(placed_file_export_path, "w", encoding="utf-8") as f:
            f.write("SKU,Y (mm),X (mm),Z (mm),Rotate,% Cube,% Wgt,Priority,Out\n")
            for line in export_lines:
                f.write(line + "\n")

        show_temporary_message("Success", f"Results exported successfully!\nPlaced: {placed_file_export_path}", duration=3000)
        logging.info(f"Exported {len(export_lines)} rows to {placed_file_export_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Error exporting results: {e}")
        logging.error(f"Error exporting results: {e}")


def show_temporary_message(title: str, message: str, duration: int = 1000):
    """แสดงข้อความชั่วคราวในหน้าต่าง Toplevel"""
    root = tk.Toplevel()
    root.title(title)
    width, height = 300, 100
    root.geometry(f"{width}x{height}")
    root.resizable(False, False)
    # คำนวณให้หน้าต่างอยู่กลางจอ
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # เพิ่มข้อความในหน้าต่าง
    label = tk.Label(root, text=message, wraplength=280, justify="center")
    label.pack(expand=True, fill="both", padx=10, pady=10)

    # ตั้งเวลาให้ปิดหน้าต่างอัตโนมัติ
    root.after(duration, root.destroy)