"""
applog.py - Central log buffer.

Every module that used to call rich's Console().print() directly now
routes through log() here instead -- it still prints to the terminal
exactly as before, but also keeps a rolling buffer the GUI can poll,
so the dashboard shows the same "You: ..." / "Maggie: ..." / error
lines you'd see in the terminal, live.
"""
from collections import deque
from datetime import datetime
from rich.console import Console

console = Console()
_LOG_BUFFER = deque(maxlen=200)


def log(text: str, style: str = ""):
    """Prints to terminal (with optional rich style) and stores a plain
    (no markup) timestamped copy for the GUI."""
    if style:
        console.print(f"[{style}]{text}[/{style}]")
    else:
        console.print(text)
    timestamp = datetime.now().strftime("%H:%M:%S")
    _LOG_BUFFER.append(f"[{timestamp}] {text}")


def get_recent_logs(n: int = 40):
    return list(_LOG_BUFFER)[-n:]
