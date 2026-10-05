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

import alarms
import applog
import brain
import greeting
import gui
import language
import listener
import memory
import metrics
import routines
from speaker import speak
import status
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

    applog.log("Maggie Systems Online.", style="bold magenta")
    status.set_status("idle", "Online")
    speak(greeting.build_greeting("Kavin"))

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

            if any(
                phrase in q_lower
                for phrase in ("learn my voice", "enroll my voice")
            ):
                status.set_status("listening", "Enrolling owner voice...")
                speak(
                    "I will listen to five short samples now. Only derived voice features "
                    "are saved locally; the audio is discarded. This is not secure authentication."
                )
                try:
                    enrolled = listener.enroll_owner(mic)
                except Exception as e:
                    applog.log(f"Voice enrollment failed: {e}", style="red")
                    enrolled = False
                status.set_flag("voice_profile_enrolled", enrolled)
                status.set_flag("owner_voice_match", False)
                speak(
                    "Your local voice profile is ready."
                    if enrolled
                    else "I could not complete voice enrollment. Please try again in a quiet place."
                )
                continue

            # Sleep Mode Verification
            if flags["sleeping"]:
                if "wake up" in q_lower or "maggie wake up" in q_lower:
                    status.set_flag("sleeping", False)
                    try:
                        import voice_identity

                        status.set_flag("voice_profile_enrolled", voice_identity.is_enrolled())
                    except Exception as e:
                        applog.log(f"Could not inspect the local voice profile: {e}", style="yellow")
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
                # Same mode set_mode() persisted -- consistent with what
                # was used to decode input and prompt the LLM, not a fresh
                # per-reply guess.
                speak(answer, voice=language.tts_voice_for(language.get_mode()))

            if status.get_flags()["exit_requested"]:
                _cleanup_and_exit()

        except Exception as e:
            applog.log(f"Voice Loop Exception: {e}", style="red")
            time.sleep(0.4)

def main():
    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    status.set_flag("exit_requested", False)
    status.set_flag("muted", False)
    status.set_flag("paused", False)
    status.set_flag("sleeping", False)

    # Voice, reminders, and telemetry are useful even if the dashboard cannot
    # obtain a native GUI thread (common on constrained Linux systems).
    voice_thread = threading.Thread(target=voice_loop, name="maggie-voice", daemon=True)
    try:
        voice_thread.start()
    except RuntimeError as e:
        applog.log(f"Could not start voice worker: {e}; running voice loop in main thread.", style="yellow")
        # Avoid starting auxiliary threads when the process has no spare
        # thread slots; the voice loop is the core function.
        voice_loop()
        return

    for label, start_worker in (
        ("alarms", lambda: alarms.start(on_trigger=speak)),
        ("routines", lambda: routines.start(on_trigger=speak)),
        ("telemetry", lambda: metrics.start(on_critical_failure=speak)),
    ):
        try:
            start_worker()
        except RuntimeError as e:
            applog.log(f"Could not start {label} worker: {e}", style="yellow")

    try:
        gui.run()
    except Exception as e:
        applog.log(f"GUI unavailable: {e}. Voice assistant will continue without the dashboard.", style="yellow")
        # Keep the application alive in headless mode rather than exiting after
        # a Qt/PyQt thread creation failure.
        while voice_thread.is_alive() and not status.get_flags().get("exit_requested", False):
            voice_thread.join(timeout=0.5)
    finally:
        if not status.get_flags().get("exit_requested", False):
            _cleanup_and_exit()

if __name__ == "__main__":
    main()
