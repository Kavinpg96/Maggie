"""
system_control.py - Local Execution Engine
Handles app launching, web actions, media playback, and social navigation.
"""
import re
import subprocess
import webbrowser
from rich.console import Console

console = Console()

WEB_SITES = {
    "gmail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "inbox": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "fb": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "insta": "https://www.instagram.com",
    "youtube": "https://www.youtube.com",
    "chrome": "https://www.google.com",
}

APP_COMMANDS = {
    "terminal": ["gnome-terminal"],
    "files": ["nautilus"],
    "code": ["code"],
    "vscode": ["code"],
    "settings": ["gnome-control-center"],
    "spotify": ["spotify"],
    "calculator": ["gnome-calculator"],
}

_PLAY_RE = re.compile(r"\bplay\b", re.IGNORECASE)
_FILLER_RE = re.compile(
    r"\b(ok|okay|please|can you|could you|would you|hey|maggie|"
    r"a song|song|for me|in youtube|on youtube|youtube|track|music)\b",
    re.IGNORECASE,
)


def _extract_song(query: str) -> str:
    """Strips wake words / politeness / filler from a play command,
    e.g. 'ok play a song for me in youtube tamil song' -> 'tamil'."""
    cleaned = _PLAY_RE.sub("", query)
    cleaned = _FILLER_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def handle_execution(query: str):
    q = query.lower().strip()

    # Play song on YouTube - matches "play" anywhere in the sentence,
    # not just at the very start, so "ok play <song>" works too.
    if _PLAY_RE.search(q):
        song = _extract_song(q)
        if song:
            try:
                import pywhatkit
                pywhatkit.playonyt(song)
                return f"Playing {song} on YouTube."
            except Exception:
                webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
                return f"Searching and playing {song} on YouTube."
        return "What would you like me to play?"

    # Open Social / Web / Apps
    if "open" in q or "launch" in q or "go to" in q:
        for site, url in WEB_SITES.items():
            if site in q:
                webbrowser.open(url)
                return f"Opening {site.capitalize()}."

        for app, cmd in APP_COMMANDS.items():
            if app in q:
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Launching {app.capitalize()}."
                except Exception as e:
                    return f"Failed to launch {app}: {e}"

    return None
