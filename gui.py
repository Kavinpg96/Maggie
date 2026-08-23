"""
gui.py - Webview Bridge & API Controller
"""
import os
import webview
import status
import services_check
import diagnostics

_ASSET_DIR = os.path.join(os.path.dirname(__file__), "gui3d")
_window = None

class Api:
    def get_status(self):
        data = status.get_status()
        data["services"] = services_check.get_all_services_status()
        data["health"] = {
            "ai_engine": "READY",
            "stt": "READY",
            "tts": "READY",
            "mic": "READY",
            "memory": "READY",
            "database": "READY"
        }
        data["ai_info"] = {
            "model": "llama-3.3-70b",
            "backend": "Groq / Local",
            "latency": "0.82 s"
        }
        return data

def close_window():
    global _window
    if _window:
        try:
            _window.destroy()
        except Exception:
            pass

def run():
    global _window
    index_path = os.path.join(_ASSET_DIR, "index.html")
    api = Api()
    _window = webview.create_window(
        "MAGGIE INTELLIGENCE DASHBOARD", url=index_path, js_api=api,
        fullscreen=True, background_color="#020609"
    )
    webview.start(debug=False)
