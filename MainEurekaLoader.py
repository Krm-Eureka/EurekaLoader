import os
import sys
import logging
import tkinter as tk
from Service.UI import PackingApp
from Service.config_manager import load_config

# --- Load Configuration ---
try:
    config, base_dir = load_config()
except RuntimeError as e:
    print(f"Configuration Error: {e}")
    sys.exit(1)

# --- Logging ---
logging.basicConfig(
    filename=os.path.join(base_dir, "appLogging.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

# --- Loader Application ---
class LoaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Loading EurekaLoader")
        self.root.geometry("500x350")
        self.root.resizable(False, False)

        # Center the window on the screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (350 // 2)
        self.root.geometry(f"500x350+{x}+{y}")

        # ใช้ Canvas เพื่อวาดพื้นหลัง
        self.canvas = tk.Canvas(self.root, width=500, height=350, highlightthickness=0, bg="#f0f0f0")
        self.canvas.pack(fill="both", expand=True)

        # เพิ่มโลโก้ EA_Logo.png
        logo_path = os.path.join(base_dir, "EA_Logo.png")
        self.logo = tk.PhotoImage(file=logo_path)
        self.logo_label = tk.Label(self.root, image=self.logo, bg="#f0f0f0")
        self.logo_label.place(relx=0.5, rely=0.3, anchor="center")

        # Progress bar
        self.progress_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.progress_frame.place(relx=0.5, rely=0.6, anchor="center")
        self.progress = tk.Canvas(self.progress_frame, width=400, height=20, bg="white", highlightthickness=0)
        self.progress.pack()
        self.progress_bar = self.progress.create_rectangle(0, 0, 0, 20, fill="#4682b4", width=0)

        # Status label
        self.progress_label = tk.Label(
            self.root,
            text="Initializing...",
            font=("Arial", 12),
            bg="#f0f0f0",
            fg="#555555",
        )
        self.progress_label.place(relx=0.5, rely=0.75, anchor="center")

        # Start updating progress bar
        self.update_progress()

    def update_progress(self):
        """Update the progress bar."""
        current_width = self.progress.coords(self.progress_bar)[2]
        if current_width < 400:
            self.progress.coords(self.progress_bar, 0, 0, current_width + 10, 20)
            self.progress_label.config(text=f"Loading... {int((current_width / 400) * 100)}%")
            self.root.after(100, self.update_progress)
        else:
            self.progress_label.config(text="Loading Complete!")
            self.root.after(500, self.start_main_app)

    def start_main_app(self):
        """Start the main application."""
        self.root.destroy()
        root = tk.Tk()
        root.state('zoomed') 
        root.lift() # ยกหน้าต่างขึ้นมา root.attributes('-topmost', True)

        app = PackingApp(root, base_dir)
        logging.info("Application started.")
        root.mainloop()
        

# --- Main Application ---
def main():
    root = tk.Tk()
    loader = LoaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()