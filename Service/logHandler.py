import os
import re
import time
import logging
from datetime import datetime, timezone
from logging.handlers import BaseRotatingHandler
from Service.config_manager import load_config

# ==============================
#  Handler: หมุนไฟล์ตามเดือน + เก็บใน ./MonthlyLogging
# ==============================
class MonthlyRotatingFileHandler(BaseRotatingHandler):
    """
    สร้างไฟล์ใหม่ทุกต้นเดือน และย้ายไฟล์ของเดือนก่อนหน้าไปไว้ในโฟลเดอร์ archive
    ชื่อไฟล์เก่าจะเป็น: <base>-YYYY-MM<ext>  เช่น Logging-2025-08.log
    """
    def __init__(self, filename, mode="a", encoding=None, delay=False,
                 backupCount=12, utc=False, archive_dir="MonthlyLogging"):
        super().__init__(filename, mode, encoding, delay)
        self.backupCount = backupCount
        self.utc = utc
        self.suffix = "%Y-%m"

        # ทำ path โฟลเดอร์เก็บไฟล์เก่าให้อยู่ใต้โฟลเดอร์เดียวกับไฟล์หลักเสมอ
        root_dir = os.path.dirname(os.path.abspath(self.baseFilename)) or "."
        self.archive_dir = archive_dir
        if not os.path.isabs(self.archive_dir):
            self.archive_dir = os.path.join(root_dir, self.archive_dir)
        os.makedirs(self.archive_dir, exist_ok=True)

        # เวลา rollover ครั้งถัดไป = ต้นเดือนถัดไป 00:00:00
        self.rolloverAt = self._compute_next_month_boundary(time.time())

        # ถ้าไฟล์ปัจจุบันเป็นของเดือนก่อนหน้า ให้ rollover ทันที
        try:
            stat = os.stat(self.baseFilename)
            if stat and (not self._is_same_month(stat.st_mtime, time.time())):
                self.doRollover()
        except FileNotFoundError:
            pass

    def _is_same_month(self, t1, t2):
        dt1 = datetime.fromtimestamp(t1)
        dt2 = datetime.fromtimestamp(t2)
        return (dt1.year == dt2.year) and (dt1.month == dt2.month)

    def _compute_next_month_boundary(self, current_time):
        dt = datetime.fromtimestamp(current_time, timezone.utc) if self.utc else datetime.fromtimestamp(current_time)
        year, month = dt.year, dt.month
        next_month = datetime(year + (month == 12), (month % 12) + 1, 1)
        return next_month.timestamp()

    def shouldRollover(self, record):
        return time.time() >= self.rolloverAt

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        # ชื่อไฟล์ของ "เดือนที่เพิ่งจบ" -> ย้ายเข้า archive_dir
        t = self.rolloverAt - 1  # ย้อน 1 วินาที เพื่อชัวร์ว่าเป็นเดือนก่อนหน้า
        dt = datetime.fromtimestamp(t, timezone.utc) if self.utc else datetime.fromtimestamp(t)
        base_name = os.path.splitext(os.path.basename(self.baseFilename))[0]
        ext = os.path.splitext(self.baseFilename)[1]
        archived_name = f"{base_name}-{dt.strftime(self.suffix)}{ext}"
        dfn = os.path.join(self.archive_dir, archived_name)

        # ถ้ามีไฟล์ปลายทางแล้ว ให้ลบทิ้งก่อน
        if os.path.exists(dfn):
            try:
                os.remove(dfn)
            except OSError:
                pass

        # ย้ายไฟล์ปัจจุบันเข้า archive
        if os.path.exists(self.baseFilename):
            try:
                os.replace(self.baseFilename, dfn)  # ปลอดภัยกว่า rename บนบาง OS
            except OSError:
                # ถ้า cross-device ให้ copy แล้วลบ
                import shutil
                shutil.copy2(self.baseFilename, dfn)
                try:
                    os.remove(self.baseFilename)
                except OSError:
                    pass

        # ลบไฟล์เก่าเกิน backupCount ภายใน archive_dir
        if self.backupCount > 0:
            for s in self._get_files_to_delete(base_name, ext):
                try:
                    os.remove(os.path.join(self.archive_dir, s))
                except OSError:
                    pass

        # เปิดไฟล์ใหม่ของเดือนปัจจุบัน
        if not self.delay:
            self.stream = self._open()

        # คำนวณเส้นตายเดือนถัดไป
        self.rolloverAt = self._compute_next_month_boundary(time.time())

    def _get_files_to_delete(self, base_name, ext):
        """
        หาไฟล์รูปแบบ <base>-YYYY-MM<ext> ใน archive_dir แล้วคงไว้แค่ล่าสุด backupCount รายการ
        """
        pattern = re.compile(rf"^{re.escape(base_name)}-\d{{4}}-\d{{2}}{re.escape(ext)}$")
        candidates = []
        try:
            for fn in os.listdir(self.archive_dir):
                if pattern.match(fn):
                    candidates.append(fn)
        except FileNotFoundError:
            return []

        candidates.sort()  # YYYY-MM เรียง lexicographic = ตามเวลาได้เลย
        num_to_delete = max(0, len(candidates) - self.backupCount)
        return candidates[:num_to_delete]


# ==============================
#  การตั้งค่าใช้งาน
# ==============================
config, base_dir = load_config()
os.makedirs(base_dir, exist_ok=True)

log_format = "%(asctime)s - %(levelname)s - %(message)s"
info_log_path = os.path.join(base_dir, "Logging.log")
debug_log_path = os.path.join(base_dir, "DEBUGLog.log")
archive_dir = os.path.join(base_dir, "MonthlyLogging")  # <- เก็บไฟล์ย้อนหลังที่นี่

# INFO: หมุนรายเดือน เก็บย้อนหลัง 12 เดือน
info_handler = MonthlyRotatingFileHandler(
    info_log_path, mode="a", encoding="utf-8", backupCount=12, archive_dir=archive_dir
)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))

# DEBUG: หมุนรายเดือน เก็บย้อนหลัง 6 เดือน
debug_handler = MonthlyRotatingFileHandler(
    debug_log_path, mode="a", encoding="utf-8", backupCount=6, archive_dir=archive_dir
)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(log_format))

# Console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# Root logger
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(info_handler)
root_logger.addHandler(debug_handler)
root_logger.addHandler(console_handler)

logging.info("🔥 Logging system initialized (monthly rotation to ./MonthlyLogging).")
logging.debug("🐞 Debug log ready (monthly rotation).")

# ลด noise ของ matplotlib
logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
logging.debug("🐞 Matplotlib font manager debug log disabled.")
print("📂 Log file (INFO):", info_log_path)



# บังคับ rollover ตอนนี้เลย
info_handler.doRollover()
debug_handler.doRollover()

logging.info("🔁 Forced monthly rollover (manual)")
print("📂 Archive dir:", archive_dir)