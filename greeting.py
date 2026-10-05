"""
greeting.py - Builds Maggie's boot greeting: "Hi Kavin" + time-of-day +
date + current weather, instead of a static "Maggie is online" line.
"""
from datetime import datetime

import web_answer

try:
    from config import HOME_LOCATION
except ImportError:
    HOME_LOCATION = "Chennai"


def _time_of_day_greeting(hour: int) -> str:
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 21:
        return "Good evening"
    return "Good night"


def build_greeting(name: str = "Kavin") -> str:
    now = datetime.now()
    time_greeting = _time_of_day_greeting(now.hour)
    date_str = now.strftime("%A, %B %d")

    weather_line = ""
    try:
        weather_line = web_answer.fetch_weather(HOME_LOCATION)
    except Exception:
        weather_line = ""

    parts = [f"Hi {name}, {time_greeting}.", f"Today is {date_str}."]
    # Only include weather if the fetch actually succeeded — an error
    # string here would get spoken out loud otherwise.
    if weather_line and "failed" not in weather_line.lower():
        parts.append(weather_line)

    return " ".join(parts)
