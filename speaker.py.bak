"""
speaker.py - Thread-Safe Speech Synthesis Engine for Maggie
"""
import asyncio
import json
import os
import platform
import subprocess
import threading
import edge_tts
from rich.console import Console
from config import TTS_VOICE, AUDIO_OUT_PATH, VOICE_POOL

console = Console()
_VOICE_STATE_PATH = os.path.join(os.path.dirname(__file__), "data", "voice_state.json")
_speak_lock = threading.Lock()


def _load_current_voice() -> str:
    try:
        with open(_VOICE_STATE_PATH) as f:
            return json.load(f).get("voice", TTS_VOICE)
    except Exception:
        return TTS_VOICE


def _save_current_voice(voice: str):
    try:
        os.makedirs(os.path.dirname(_VOICE_STATE_PATH), exist_ok=True)
        with open(_VOICE_STATE_PATH, "w") as f:
            json.dump({"voice": voice}, f)
    except Exception:
        pass


def cycle_voice() -> str:
    current = _load_current_voice()
    pool = VOICE_POOL if current in VOICE_POOL else [current] + VOICE_POOL
    idx = pool.index(current) if current in pool else -1
    next_voice = pool[(idx + 1) % len(pool)]
    _save_current_voice(next_voice)
    return next_voice


async def _generate_audio(text: str, path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


def _play_audio(path: str):
    system = platform.system()
    try:
        if system == "Linux":
            with open(os.devnull, "w") as devnull:
                subprocess.run(
                    ["mpg123", "-o", "pulse", "-q", path],
                    stdout=devnull,
                    stderr=devnull,
                    check=False,
                )
        elif system == "Darwin":
            subprocess.run(["afplay", path], check=False)
        else:
            os.startfile(path)
    except Exception:
        pass


def speak(text: str):
    """Main entry point used across the app to speak text out loud."""
    if not text:
        return

    with _speak_lock:
        console.print(f"[bold cyan]Maggie:[/bold cyan] {text}")
        voice = _load_current_voice()
        try:
            asyncio.run(_generate_audio(text, AUDIO_OUT_PATH, voice))
            _play_audio(AUDIO_OUT_PATH)
        except Exception as e:
            console.print(f"[red]Audio synthesis error: {e}[/red]")
