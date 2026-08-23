"""
Simple spoken alarm / reminder system.
Alarms live in data/alarms.json and are checked once every 20s by a
background thread. When one is due, it fires a callback (usually
main.py's maybe_speak) and removes itself.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta

ALARMS_PATH = os.path.join(os.path.dirname(__file__), "data", "alarms.json")
_lock = threading.Lock()

_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)


def _load():
    try:
        with open(ALARMS_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def _save(alarms):
    try:
        os.makedirs(os.path.dirname(ALARMS_PATH), exist_ok=True)
        with open(ALARMS_PATH, "w") as f:
            json.dump(alarms, f)
    except Exception:
        pass


def parse_alarm_time(text: str):
    """
    Small parser for phrases like:
      'set alarm 8am tomorrow', 'set an alarm for 7:30 pm today', 'set alarm 21:00'
    Returns a future datetime, or None if it can't be parsed.
    """
    text = text.lower()
    m = _TIME_RE.search(text)
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

    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if "tomorrow" in text:
        target += timedelta(days=1)
    elif target <= now:
        # already passed today and "today" wasn't said explicitly -> assume tomorrow
        target += timedelta(days=1)

    return target


def add_alarm(when: datetime, label: str = "Alarm"):
    with _lock:
        alarms = _load()
        alarms.append({"when": when.isoformat(), "label": label})
        _save(alarms)


def _checker_loop(on_trigger):
    while True:
        try:
            with _lock:
                alarms = _load()
                now = datetime.now()
                due, remaining = [], []
                for a in alarms:
                    when = datetime.fromisoformat(a["when"])
                    (due if when <= now else remaining).append(a)
                if due:
                    _save(remaining)
            for a in due:
                on_trigger(f"{a['label']}! It's {datetime.now().strftime('%I:%M %p')}.")
        except Exception:
            pass
        time.sleep(20)


def start(on_trigger):
    """on_trigger(text) is called (e.g. maybe_speak) when an alarm fires."""
    threading.Thread(target=_checker_loop, args=(on_trigger,), daemon=True).start()
