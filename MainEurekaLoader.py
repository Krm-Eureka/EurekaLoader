import os
import logging
import tkinter as tk
from Service.UI import PackingApp
from Service.config_manager import load_config, get_base_dir

# --- Load Configuration ---
config = load_config()
base_dir = config.get("Paths", "base_dir", fallback=get_base_dir())

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

# --- Main Application ---
def main():
    root = tk.Tk()
    app = PackingApp(root, base_dir)
    logging.info("Application started.")  # ย้ายมาหลังจากสร้าง PackingApp
    root.mainloop()

if __name__ == "__main__":
    main()