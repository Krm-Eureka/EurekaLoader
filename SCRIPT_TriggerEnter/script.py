# script.py  (20/09/2025)
# - Timing รายเฟสละเอียด: init, list windows, inspect, focus attempts, first enter, wait loop
# - Log parent process/working dir
# - Heartbeat: Focus.running (ลบเมื่อจบ)  /// ไม่สร้าง Focus.done ///
# - บังคับโฟกัส, ตรวจไฟล์, เพดานกด, timeout

import os
import sys
import time
import glob
import logging
import threading
from pathlib import Path
from datetime import datetime
from time import perf_counter as highres_time

# ===== Timing Helpers =====
phase_timestamps: dict[str, float] = {}   # เก็บ checkpoint แต่ละ phase

def mark_phase(name: str) -> None:
    """บันทึกเวลา ณ จุดสำคัญ"""
    phase_timestamps[name] = highres_time()

def phase_duration(start: str, end: str, default: float = 0.0) -> float:
    """คำนวณเวลาระหว่าง 2 phase"""
    if start in phase_timestamps and end in phase_timestamps:
        return phase_timestamps[end] - phase_timestamps[start]
    return default

mark_phase("t0_import")  # เริ่มนับเมื่อโหลดไฟล์นี้

# ===== CONFIG =====
CASE = "PROD"  # "DEV" | "PROD"

SEARCH_KEYWORD = "Eureka Loader Application"
PROCESS_NAME   = "python.exe"     # ชื่อ .exe ของโปรแกรมเป้าหมาย

WATCH_DIR_MAP = {
    "DEV":  Path(r"D:\KRM\25\EurekaLoader\Data"),
    "PROD": Path(r"D:\EurekaLoader\Data"),
}
WATCH_DIR = WATCH_DIR_MAP.get(CASE, WATCH_DIR_MAP["DEV"])

FILE_PATTERN          = "forexport.txt"
SEARCH_RECURSIVE      = True
DELAY_AFTER_FOCUS     = 0.30
DELAY_BETWEEN_KEYS    = 0.30
MAX_WAIT_SECONDS      = 30
MAX_KEY_PRESSES       = 100

LOG_DIR_MAP = {
    "DEV":  Path(r"D:\KRM\25\EurekaLoader\Data\focusScriptLogs"),
    "PROD": Path(r"D:\EurekaLoader\_internal\focusScriptLogs"),
}
LOG_DIR      = LOG_DIR_MAP.get(CASE, Path("focusScriptLogs"))
LOG_BASENAME = "focus"

# ===== Global accumulators (ใช้วัด overhead) =====
total_sleep_time   = 0.0
total_filecheck_time = 0.0
total_refocus_time = 0.0
refocus_count      = 0

def tracked_sleep(dt: float) -> None:
    """sleep พร้อมสะสมเวลาที่เสียไปเพื่อใช้รายงาน"""
    global total_sleep_time
    t0 = highres_time()
    time.sleep(dt)
    total_sleep_time += (highres_time() - t0)

# ===== Logging =====
def setup_monthly_logger() -> logging.Logger:
    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    month_tag = datetime.now().strftime("%Y-%m")

    candidates = [
        LOG_DIR / f"{LOG_BASENAME}_{month_tag}.log",
        base_dir / "focusScriptLogs" / f"{LOG_BASENAME}_{month_tag}.log",
        Path.cwd() / "focusScriptLogs" / f"{LOG_BASENAME}_{month_tag}.log",
    ]

    logger = logging.getLogger("focus_script")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    chosen_path = None
    last_error  = None
    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(path, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            chosen_path = path
            break
        except Exception as e:
            last_error = e

    if chosen_path:
        logger.info(f"📝 Log file: {chosen_path}")
    else:
        logger.warning(f"⚠️ Cannot create log file (last error: {last_error}); console-only logging.")

    return logger

# ===== Heartbeat (Focus.running) =====
def start_heartbeat(status_dir: Path, logger):
    """สร้างไฟล์ Focus.running และอัปเดตทุกวินาที"""
    status_dir.mkdir(parents=True, exist_ok=True)
    running_path = status_dir / "Focus.running"

    with open(running_path, "w", encoding="utf-8") as f:
        f.write(f"pid={os.getpid()} started={datetime.now().isoformat()}\n")

    stop_event = threading.Event()

    def _beat():
        while not stop_event.is_set():
            try:
                os.utime(running_path, None)
            except Exception:
                pass
            time.sleep(1.0)

    t = threading.Thread(target=_beat, name="heartbeat", daemon=True)
    t.start()
    logger.info(f"Heartbeat started: {running_path}")
    return stop_event, running_path

def clear_heartbeat(running_path: Path, logger):
    try:
        if running_path and running_path.exists():
            running_path.unlink(missing_ok=True)
            logger.debug(f"Removed heartbeat file: {running_path}")
    except Exception as e:
        logger.warning(f"Failed to remove heartbeat: {e}")

# ===== Utils =====
def hwnd_process_name(hwnd: int) -> str:
    try:
        import psutil, win32process
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name()
    except Exception as e:
        return f"<proc-err:{e}>"

def find_txt_file(directory: Path, pattern: str, recursive: bool, logger=None) -> Path | None:
    global total_filecheck_time
    t0 = highres_time()
    try:
        if not directory.exists():
            if logger:
                logger.warning(f"Directory not found: {directory}")
            return None

        pat = str(directory / ("**/" + pattern if recursive else pattern))
        matches = glob.glob(pat, recursive=recursive)
        if matches:
            newest = max(matches, key=lambda p: os.path.getmtime(p))
            return Path(newest)
        return None
    finally:
        total_filecheck_time += (highres_time() - t0)

def remove_old_file(directory: Path, pattern: str, recursive: bool, logger):
    """ลบไฟล์ export.txt อันเก่าก่อนเริ่ม run (ถ้ามี)"""
    try:
        pat = str(directory / ("**/" + pattern if recursive else pattern))
        matches = glob.glob(pat, recursive=recursive)
        if not matches:
            logger.info(f"No old '{pattern}' file found → skip cleanup")
            return

        for f in matches:
            try:
                os.remove(f)
                logger.info(f"🗑️ Removed old file: {f}")
            except Exception as e:
                logger.warning(f"Failed to remove old file {f}: {e}")
    except Exception as e:
        logger.warning(f"remove_old_file() error: {e}")

# ===== Focus =====
def focus_with_pygetwindow(keyword: str, timeout: float, expect_proc: str, logger):
    import pygetwindow as gw
    stats = {"titles": 0, "inspect_time": 0.0, "activate_attempts": 0, "activate_time": 0.0}

    mark_phase("t2_list_begin")
    titles = [t for t in gw.getAllTitles() if t.strip()]
    mark_phase("t2_list_end")
    logger.info(f"Scanning {len(titles)} window(s) ...")
    stats["titles"] = len(titles)

    mark_phase("t2i_inspect_begin")
    candidates = []
    for idx, t in enumerate(titles, start=1):
        try:
            wins = gw.getWindowsWithTitle(t)
            if not wins:
                continue
            win = wins[0]
            hwnd = int(getattr(win, "_hWnd", 0))
            pname = hwnd_process_name(hwnd)
            logger.info(f"  [{idx}] title='{t}', hwnd={hwnd}, proc={pname}")
            if keyword.lower() in t.lower() and pname.lower() == expect_proc.lower():
                candidates.append((t, win, hwnd, pname))
        except Exception as e:
            logger.warning(f"  [{idx}] inspect failed: {e}")
    mark_phase("t2i_inspect_end")
    stats["inspect_time"] = phase_duration("t2i_inspect_begin", "t2i_inspect_end")

    if not candidates:
        logger.error(f"No matching window → need title contains '{keyword}' AND process='{expect_proc}'")
        return None, None, None, stats

    # เลือก title ที่ยาวสุด
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    title, win, hwnd, pname = candidates[0]
    logger.info(f"Selected window: '{title}', hwnd={hwnd}, proc={pname}")

    try:
        if win.isMinimized:
            logger.info("Window minimized → restoring")
            win.restore()
    except Exception as e:
        logger.warning(f"Restore failed: {e}")

    mark_phase("t3_focus_begin")
    t_deadline = time.time() + timeout
    while time.time() < t_deadline:
        try:
            t0 = highres_time()
            win.activate()
            stats["activate_attempts"] += 1
            tracked_sleep(0.05)
            stats["activate_time"] += (highres_time() - t0)
            if win.isActive:
                mark_phase("t3_focus_ok")
                logger.info(f"Successfully focused: '{title}' (hwnd={hwnd}) "
                            f"attempts={stats['activate_attempts']}, actTime={stats['activate_time']:.3f}s")
                return title, win, hwnd, stats
        except Exception as e:
            logger.warning(f"Activate failed (สิทธิ์อาจไม่เท่ากัน): {e}")
        tracked_sleep(0.15)

    logger.error(f"Can't focus within {timeout:.1f}s")
    return None, None, None, stats

# ===== Main =====
def main():
    import pyautogui, pygetwindow as gw
    pyautogui.PAUSE = 0
    pyautogui.FAILSAFE = False

    mark_phase("t1_logger_begin")
    logger = setup_monthly_logger()
    mark_phase("t1_logger_ready")

    # context info
    logger.info("=== Script start ===")
    remove_old_file(WATCH_DIR, FILE_PATTERN, SEARCH_RECURSIVE, logger)
    logger.info("Exit codes: 0=OK | 1=NoWindow | 2=Timeout | 3=PressCap | 99=Unexpected")
    logger.info(f"Config: CASE={CASE}, KEYWORD={SEARCH_KEYWORD}, EXPECT_PROC={PROCESS_NAME}")
    logger.info(f"Dir={WATCH_DIR}, Pattern={FILE_PATTERN}, Timeout={MAX_WAIT_SECONDS}, MaxPress={MAX_KEY_PRESSES}")
    try:
        import psutil
        parent = psutil.Process(os.getppid()).name()
        logger.info(f"Parent process: {parent} (pid={os.getppid()})  | exe={sys.executable} | cwd={os.getcwd()}")
    except Exception as e:
        logger.info(f"Parent process detect failed: {e}")

    # Heartbeat
    stop_hb, running_path = start_heartbeat(LOG_DIR, logger)

    # Focus window
    mark_phase("t2_focus_entry")
    title, target_win, hwnd, fstats = focus_with_pygetwindow(
        SEARCH_KEYWORD, timeout=30, expect_proc=PROCESS_NAME, logger=logger
    )
    if not title:
        clear_heartbeat(running_path, logger)
        logger.info("⏱ Breakdown: init=%.2fs, list=%.2fs, inspect=%.2fs" % (
            phase_duration("t0_import", "t1_logger_ready"),
            phase_duration("t2_list_begin", "t2_list_end"),
            fstats.get("inspect_time", 0.0),
        ))
        sys.exit(1)
    # remove_old_file(WATCH_DIR, FILE_PATTERN, SEARCH_RECURSIVE, logger)
    
    tracked_sleep(DELAY_AFTER_FOCUS)
    mark_phase("t4_post_focus")

    # First trigger enter
    pyautogui.press("enter")
    mark_phase("t5_first_enter")
    logger.info("Enter pressed once immediately after focus/restore (trigger update)")
    tracked_sleep(DELAY_BETWEEN_KEYS)

    # Loop
    start_loop = time.time()
    presses = 1
    logger.info("Start pressing Enter until file is detected or timeout/press limit reached")

    global total_refocus_time, refocus_count
    while True:
        # file check
        found = find_txt_file(WATCH_DIR, FILE_PATTERN, SEARCH_RECURSIVE, logger)
        if found:
            mark_phase("t6_found")
            clear_heartbeat(running_path, logger)

            # detailed timing summary
            init   = phase_duration("t0_import", "t1_logger_ready")
            lst    = phase_duration("t2_list_begin", "t2_list_end")
            insp   = fstats.get("inspect_time", 0.0)
            foc    = phase_duration("t3_focus_begin", "t3_focus_ok", 0.0)
            firstE = phase_duration("t3_focus_ok", "t5_first_enter", 0.0)
            loopd  = phase_duration("t5_first_enter", "t6_found", 0.0)
            total  = phase_duration("t0_import", "t6_found", 0.0)

            logger.info(f"✅ Stop reason: found='{found}' (pressed={presses})")
            logger.info("⏱ Breakdown: init=%.2fs, list=%.2fs, inspect=%.2fs, focus=%.2fs, "
                        "firstEnter=%.2fs, loopWait=%.2fs, total=%.2fs" %
                        (init, lst, insp, foc, firstE, loopd, total))
            logger.info("   Extra: activateAttempts=%d, activateTime=%.2fs, "
                        "refocusCount=%d/%.2fs, fileChecks=%.2fs, sleeps=%.2fs" %
                        (fstats.get("activate_attempts", 0), fstats.get("activate_time", 0.0),
                         refocus_count, total_refocus_time, total_filecheck_time, total_sleep_time))
            sys.exit(0)

        # ensure focus stays on target
        try:
            active = gw.getActiveWindow()
            if not active or int(getattr(active, "_hWnd", 0)) != int(hwnd):
                t0 = highres_time()
                logger.warning("Focus lost → bringing back target window")
                target_win.activate()
                tracked_sleep(0.20)
                total_refocus_time += (highres_time() - t0)
                refocus_count += 1
        except Exception as e:
            t0 = highres_time()
            logger.warning(f"Check active window failed → re-activate: {e}")
            target_win.activate()
            tracked_sleep(0.20)
            total_refocus_time += (highres_time() - t0)
            refocus_count += 1

        # press with cap
        if presses >= MAX_KEY_PRESSES:
            clear_heartbeat(running_path, logger)
            mark_phase("t6_presscap")
            total = phase_duration("t0_import", "t6_presscap")
            logger.error(f"⛔ Stop reason: press limit {MAX_KEY_PRESSES} reached (no file) | total={total:.2f}s")
            logger.info("   Extra: fileChecks=%.2fs, sleeps=%.2fs, refocus=%d/%.2fs" %
                        (total_filecheck_time, total_sleep_time, refocus_count, total_refocus_time))
            sys.exit(3)

        pyautogui.press("enter")
        presses += 1
        logger.info(f"Enter pressed (file not found yet, count={presses})")
        tracked_sleep(DELAY_BETWEEN_KEYS)

        # timeout
        if time.time() - start_loop >= MAX_WAIT_SECONDS:
            clear_heartbeat(running_path, logger)
            mark_phase("t6_timeout")
            total = phase_duration("t0_import", "t6_timeout")
            logger.warning(f"⏹ Stop reason: timeout {MAX_WAIT_SECONDS}s (pressed={presses}) | total={total:.2f}s")
            logger.info("   Extra: fileChecks=%.2fs, sleeps=%.2fs, refocus=%d/%.2fs" %
                        (total_filecheck_time, total_sleep_time, refocus_count, total_refocus_time))
            sys.exit(2)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        sys.exit(99)
# End of script.py
#20/09/2025

# py -3.12 -m nuitka --standalone --remove-output --lto=yes --output-dir=build --windows-console-mode=disable script.py
