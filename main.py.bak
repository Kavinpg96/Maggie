"""
main.py - Maggie Entry Point
"""
import ctypes
import os
import signal
import sys
import threading
import time

# Suppress ALSA / JACK C-level stderr noise before importing audio modules
try:
    ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    def py_error_handler(filename, line, function, err, fmt):
        pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception:
    pass

import speech_recognition as sr
from rich.console import Console

import alarms
import brain
import gui
import listener
import memory
import metrics
import routines
from speaker import speak
import status

console = Console()
_PID_FILE = os.path.join(os.path.dirname(__file__), "data", "maggie.pid")

def _cleanup_and_exit(signum=None, frame=None):
    os.system("stty sane 2>/dev/null")
    status.set_flag("exit_requested", True)
    if os.path.exists(_PID_FILE):
        try:
            os.remove(_PID_FILE)
        except OSError:
            pass
    gui.close_window()
    sys.exit(0)

def voice_loop():
    memory.init_db()
    mic = sr.Microphone()
    status.set_status("idle", "Calibrating Audio...")
    listener.calibrate(mic)

    console.print("[bold magenta]Maggie Systems Online.[/bold magenta]\n")
    status.set_status("idle", "Online")
    speak("Hello Kavin, Maggie is online.")

    while not status.get_flags()["exit_requested"]:
        try:
            flags = status.get_flags()

            if flags["paused"]:
                time.sleep(0.4)
                continue

            status.set_status("listening", "Listening...")
            query = listener.listen_for_query(mic)

            if not query:
                status.set_status("idle", "Listening...")
                continue

            q_lower = query.lower()

            # Sleep Mode Verification
            if flags["sleeping"]:
                if "wake up" in q_lower or "maggie wake up" in q_lower:
                    status.set_flag("sleeping", False)
                    status.set_status("speaking", "Waking Up")
                    speak("I am awake and listening, Kavin.")
                continue

            if any(cmd in q_lower for cmd in ["go to sleep", "sleep mode", "goodnight"]):
                status.set_flag("sleeping", True)
                status.set_status("sleeping", "Asleep")
                speak("Going to sleep. Say wake up whenever you need me.")
                continue

            status.set_status("thinking", "Processing...")
            answer = brain.get_response(query)

            status.set_exchange(query, answer)
            status.set_status("speaking", "Responding...")

            if answer and not flags["muted"]:
                speak(answer)

            if status.get_flags()["exit_requested"]:
                _cleanup_and_exit()

        except Exception as e:
            console.print(f"[red]Voice Loop Exception: {e}[/red]")
            time.sleep(0.4)

def main():
    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    status.set_flag("exit_requested", False)
    status.set_flag("muted", False)
    status.set_flag("paused", False)
    status.set_flag("sleeping", False)

    threading.Thread(target=voice_loop, daemon=True).start()
    alarms.start(on_trigger=speak)
    routines.start(on_trigger=speak)
    metrics.start(on_critical_failure=speak)

    try:
        gui.run()
    except Exception as e:
        console.print(f"[yellow]GUI Exception: {e}[/yellow]")
    finally:
        _cleanup_and_exit()

if __name__ == "__main__":
    main()
