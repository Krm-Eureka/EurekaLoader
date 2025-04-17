import os
import sys
import socket
import logging
import tkinter as tk
from tkinter import messagebox
from Service.UI import PackingApp
from Service.config_manager import load_config

# --- Instance Lock Configuration ---
HOST = "127.0.0.1"
PORT = 55555

def is_another_instance_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(1)
        return False, s  # No instance running
    except OSError:
        return True, None  # Another instance is already running

# --- Loader Application ---
class LoaderApp:
    def __init__(self, root, base_dir, lock_socket):
        self.root = root
        self.lock_socket = lock_socket
        self.base_dir = base_dir
        self.root.title("Loading EurekaLoader")
        self.root.geometry("500x350")
        self.root.resizable(False, False)

        # Center the window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (350 // 2)
        self.root.geometry(f"500x350+{x}+{y}")

        # Canvas background
        self.canvas = tk.Canvas(self.root, width=500, height=350, highlightthickness=0, bg="#f0f0f0")
        self.canvas.pack(fill="both", expand=True)

        # Logo
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

        self.update_progress()

    def update_progress(self):
        current_width = self.progress.coords(self.progress_bar)[2]
        if current_width < 400:
            self.progress.coords(self.progress_bar, 0, 0, current_width + 10, 20)
            self.progress_label.config(text=f"Loading... {int((current_width / 400) * 100)}%")
            self.root.after(100, self.update_progress)
        else:
            self.progress_label.config(text="Loading Complete!")
            self.root.after(500, self.start_main_app)

    def start_main_app(self):
        self.root.destroy()
        root = tk.Tk()
        root.state('zoomed')
        icon_path = os.path.join(self.base_dir, "favicon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        app = PackingApp(root, self.base_dir)
        logging.info("Application started.")
        root.mainloop()

        # ปิด socket เมื่อโปรแกรมจบ
        if self.lock_socket:
            self.lock_socket.close()

# --- Main Function ---
def main():
    # Load config
    try:
        config, base_dir = load_config()
    except RuntimeError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)

    # Setup logging
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

    # Check for duplicate instance
    already_running, lock_socket = is_another_instance_running()
    if already_running:
        tk.Tk().withdraw()
        messagebox.showinfo("Already Running", "Eureka Loader is already open.")
        sys.exit(0)

    # Start loader window
    root = tk.Tk()
    loader = LoaderApp(root, base_dir, lock_socket)
    root.mainloop()

if __name__ == "__main__":
    main()
