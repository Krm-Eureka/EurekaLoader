import os
import pandas as pd
from tkinter import messagebox
import logging
from Models.Box import Box

def load_csv(filepath: str):
    """Load box data from a CSV file."""
    try:
        if not os.path.exists(filepath):
            # สร้างโฟลเดอร์ Input หากไม่มี
            input_folder = os.path.dirname(filepath)
            if not os.path.exists(input_folder):
                os.makedirs(input_folder)
                logging.info(f"Created folder: {input_folder}")

            # สร้างไฟล์ forimport.csv พร้อมข้อมูลตัวอย่าง
            sample_data = """Priority,BoxTypes,Width,Length,Height,Conveyor,QTY
                            1,TEST1,100,200,150,1,1
                            2,TEST2,120,220,160,1,1
                            3,TEST3,140,240,170,1,1
                            """
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(sample_data)
                logging.info(f"Created sample file: {filepath}")

            messagebox.showinfo(
                "Info", f"Sample file created: {filepath}. Please edit it and reload."
            )
            return None

        # โหลดข้อมูลจากไฟล์ CSV
        df = pd.read_csv(filepath, encoding="utf-8")
        logging.info(f"Loaded CSV file: {filepath}")

        if df.empty:
            messagebox.showerror("Error", "CSV file is empty.")
            logging.error("CSV file is empty.")
            return None

        required_columns = ["Priority", "BoxTypes", "Width", "Length", "Height", "Conveyor", "QTY"]
        for col in required_columns:
            if col not in df.columns:
                messagebox.showerror("Error", f"Missing required column: {col}")
                logging.error(f"Missing required column: {col}")
                return None

        boxes_to_place = []
        for _, row in df.iterrows():
            box = Box(
                length=row["Length"],
                width=row["Width"],
                height=row["Height"],
                sku=row["BoxTypes"],
                priority=row["Priority"],
            )
            boxes_to_place.append(box)

        messagebox.showinfo("Success", "CSV loaded successfully!")
        logging.info("CSV loaded successfully!")
        return boxes_to_place

    except pd.errors.EmptyDataError:
        messagebox.showerror("Error", f"File is empty: {filepath}")
        logging.error(f"File is empty: {filepath}")
    except pd.errors.ParserError:
        messagebox.showerror("Error", f"Error parsing CSV file: {filepath}")
        logging.error(f"Error parsing CSV file: {filepath}")
    except Exception as e:
        messagebox.showerror("Error", f"Error loading CSV: {e}")
        logging.error(f"Error loading CSV: {e}")
    return None


def export_results(placed_df, failed_df, base_dir: str):
    """Export results to CSV files."""
    try:
        placed_folder = os.path.join(base_dir, "Placed")
        failed_folder = os.path.join(base_dir, "Exception_Place")

        # Create folders if they don't exist
        if not os.path.exists(placed_folder):
            os.makedirs(placed_folder)
            logging.info(f"Created folder: {placed_folder}")
        if not os.path.exists(failed_folder):
            os.makedirs(failed_folder)
            logging.info(f"Created folder: {failed_folder}")

        # Define file paths
        placed_file_path = os.path.join(placed_folder, "forexport.csv")
        failed_file_path = os.path.join(failed_folder, "Free_Roller_Boxes.csv")

        # Export to CSV
        placed_df.to_csv(placed_file_path, index=False)
        failed_df.to_csv(failed_file_path, index=False)

        messagebox.showinfo(
            "Success",
            f"Results exported successfully!\nPlaced: {placed_file_path}\nFailed: {failed_file_path}",
        )
        logging.info(
            f"Results exported successfully!\nPlaced: {placed_file_path}\nFailed: {failed_file_path}"
        )

    except Exception as e:
        messagebox.showerror("Error", f"Error exporting results: {e}")
        logging.error(f"Error exporting results: {e}")