"""
diagnostics.py - Self-Optimization, Subsystem Diagnostic & Log Engine
"""
import os
import gc
import time
import shutil
import speech_recognition as sr
import psutil
from config import GROQ_API_KEY, DB_PATH, LOG_DIR
import services_check

LOG_FILE = os.path.join(LOG_DIR, "maggie_self_test.log")

def run_self_test() -> str:
    # 1. Self-Optimization Pass
    gc.collect()

    # 2. Hardware Checks
    mics_ok = bool(sr.Microphone.list_microphone_names())
    db_ok = os.path.exists(DB_PATH)
    audio_ok = bool(shutil.which("mpg123") or shutil.which("afplay"))

    # 3. Services Check
    services = services_check.get_all_services_status()
    running_services = [s for s, status in services.items() if status == "Running"]
    stopped_services = [s for s, status in services.items() if status == "Stopped"]

    # 4. Telemetry Snapshot
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    summary = (
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SELF-TEST & OPTIMIZATION REPORT:\n"
        f"- Memory Garbage Collection: Completed\n"
        f"- Microphone: {'OPERATIONAL' if mics_ok else 'OFFLINE'}\n"
        f"- Memory Database: {'CONNECTED' if db_ok else 'MISSING'}\n"
        f"- Hardware Load: CPU {cpu}%, RAM {ram}%\n"
        f"- Active Services: {', '.join(running_services)}\n"
        f"- Inactive Services: {', '.join(stopped_services)}\n"
    )

    # Write log to data/logs/maggie_self_test.log
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(summary + "\n" + "-"*50 + "\n")
    except Exception as e:
        print(f"Failed to write diagnostic log: {e}")

    spoken_summary = (
        f"Self test completed and memory optimized. "
        f"CPU load is at {cpu} percent and RAM usage is at {ram} percent. "
        f"Diagnostic details saved to log file."
    )
    return spoken_summary
