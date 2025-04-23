
import os
import logging
from Service.config_manager import load_config
config, base_dir = load_config()

# --- Setup logging ---
log_format = "%(asctime)s - %(levelname)s - %(message)s"
info_log_path = os.path.join(base_dir, "Logging.log")
debug_log_path = os.path.join(base_dir, "DEBUGLog.log")

# สร้าง Handler สำหรับ Logging.log (INFO ขึ้นไป)
info_handler = logging.FileHandler(info_log_path, mode="a", encoding="utf-8")
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))

# สร้าง Handler สำหรับ DEBUGLog.log (DEBUG ขึ้นไป)
debug_handler = logging.FileHandler(debug_log_path, mode="a", encoding="utf-8")
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(log_format))

# Console Handler (แสดงเฉพาะ INFO+ บนหน้าจอ)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# ล้าง handler เดิมและเพิ่มใหม่
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.DEBUG)  # Root logger รับได้ทุกระดับ

root_logger.addHandler(info_handler)
root_logger.addHandler(debug_handler)
root_logger.addHandler(console_handler)

logging.info("🔥 Logging system initialized.")
logging.debug("🐞 Debug log ready.")
# 🔇 ปิด debug log ของ matplotlib font manager
logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
logging.debug("🐞 Matplotlib font manager debug log disabled.")
