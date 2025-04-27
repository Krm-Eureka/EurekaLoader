import os
import sys
import socket
import logging
import tkinter as tk
from tkinter import messagebox
from screeninfo import get_monitors


from Service.config_manager import load_config
config, base_dir = load_config()  # ✅ Load config ก่อน logHandler
from Service import logHandler  # ✅ ใช้ base_dir เพื่อ set logging path
from Service.UI import PackingApp

# --- Instance Lock Configuration ---
HOST = "127.0.0.1"
PORT = 55555
# ✅ Force stdout/stderr to use utf-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
def is_another_instance_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(1)
        return False, s
    except OSError:
        return True, None

# --- Loader Application ---
class LoaderApp:
    def __init__(self, root, base_dir, lock_socket):
        self.root = root
        self.lock_socket = lock_socket
        self.base_dir = base_dir
        self.root.title("Loading EurekaLoader")
        self.root.geometry("500x350")
        self.root.resizable(False, False)

        # Center the window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (350 // 2)
        self.root.geometry(f"500x350+{x}+{y}")

        # Canvas
        self.canvas = tk.Canvas(self.root, width=500, height=350, highlightthickness=0, bg="#f0f0f0")
        self.canvas.pack(fill="both", expand=True)

        # Logo
        logo_path = os.path.join(base_dir, "EA_Logo.png")
        if os.path.exists(logo_path):
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
            
    def move_window_to_configured_screen(self, window):
        config, _ = load_config()
        try:
            screen_index = int(config.get("AppSettings", "screen_index", fallback="0"))
            monitors = get_monitors()

            if not monitors:
                print("⚠ No monitors detected.")
                return

            if screen_index >= len(monitors):
                print(f"⚠ Screen index {screen_index} not found. Falling back to screen 0.")
                screen_index = 0

            selected = monitors[screen_index]
            window.geometry(f"+{selected.x}+{selected.y}")
            print(f"🖥️ Window moved to screen {screen_index} at ({selected.x}, {selected.y})")
        except Exception as e:
            print(f"⚠ Error reading screen index: {e}")
            
    def start_main_app(self):
        self.root.destroy()
        root = tk.Tk()

        # ✅ ย้ายหน้าต่างไปยังหน้าจอที่ระบุใน config.ini
        self.move_window_to_configured_screen(root)
        root.state('zoomed')

        # ✅ ตั้งไอคอนถ้ามี
        icon_path = os.path.join(self.base_dir, "favicon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)

        # ✅ เรียกแอปหลัก
        app = PackingApp(root, self.base_dir)
        logging.info("✅ Application started.")
        root.mainloop()

        # ✅ ปิด socket ถ้าเปิดอยู่
        if self.lock_socket:
            self.lock_socket.close()


# --- Main Function ---
def main():
    already_running, lock_socket = is_another_instance_running()
    if already_running:
        tk.Tk().withdraw()
        messagebox.showinfo("Already Running", "Eureka Loader is already open.")
        sys.exit(0)

    logging.info("🚀 EurekaLoader starting up...")

    root = tk.Tk()
    loader = LoaderApp(root, base_dir, lock_socket)
    root.mainloop()
    


if __name__ == "__main__":
    main()
    logging.info("🔥 Application closed.")