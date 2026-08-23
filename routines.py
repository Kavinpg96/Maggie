"""
Proactive daily reminders -- separate from one-off alarms (alarms.py).
A routine fires every day at a set time until removed, e.g.
"remind me every day at 7pm to stretch". Checked once a minute; each
routine fires at most once per calendar day.
"""
import json
import os
import re
import threading
import time
from datetime import datetime

ROUTINES_PATH = os.path.join(os.path.dirname(__file__), "data", "routines.json")
_lock = threading.Lock()

_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)


def _load():
    try:
        with open(ROUTINES_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def _save(routines):
    try:
        os.makedirs(os.path.dirname(ROUTINES_PATH), exist_ok=True)
        with open(ROUTINES_PATH, "w") as f:
            json.dump(routines, f)
    except Exception:
        pass


def parse_routine(text: str):
    """Parses phrases like:
      'remind me every day at 7pm to stretch'
      'every day at 8:30 am remind me to take my medicine'
    Returns (hour, minute, label) or None."""
    text_l = text.lower()
    m = _TIME_RE.search(text_l)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    ampm = m.group(3)
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None

    # label = whatever comes after "to " if present, else the whole phrase
    if " to " in text_l:
        label = text_l.split(" to ", 1)[1].strip()
    else:
        label = "your daily reminder"
    return hour, minute, label


def add_routine(hour: int, minute: int, label: str):
    with _lock:
        routines = _load()
        routines.append({"hour": hour, "minute": minute, "label": label, "last_fired": ""})
        _save(routines)


def list_routines():
    return _load()


def _checker_loop(on_trigger):
    while True:
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            with _lock:
                routines = _load()
                changed = False
                for r in routines:
                    if r["hour"] == now.hour and r["minute"] == now.minute and r.get("last_fired") != today:
                        on_trigger(f"Reminder: {r['label']}.")
                        r["last_fired"] = today
                        changed = True
                if changed:
                    _save(routines)
        except Exception:
            pass
        time.sleep(30)


def start(on_trigger):
    threading.Thread(target=_checker_loop, args=(on_trigger,), daemon=True).start()
