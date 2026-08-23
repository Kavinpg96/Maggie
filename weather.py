"""
Free, no-API-key weather lookup.
1. Approximate location from IP -- tries a few free geolocation services
   in order, since any single one can rate-limit or go down.
2. Current weather for that location from Open-Meteo (free, no key).
"""
import requests

_WEATHER_CODES = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow", 73: "snow",
    75: "heavy snow", 80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "severe thunderstorms",
}


def _describe(code: int) -> str:
    return _WEATHER_CODES.get(code, "unusual weather")


def _geolocate():
    """Tries a few free IP-geolocation services in order. Returns
    (lat, lon, city) or raises if all of them fail."""
    attempts = [
        ("https://ipapi.co/json/", "latitude", "longitude", "city"),
        ("http://ip-api.com/json/", "lat", "lon", "city"),
        ("https://ipwho.is/", "latitude", "longitude", "city"),
    ]
    last_error = None
    for url, lat_key, lon_key, city_key in attempts:
        try:
            data = requests.get(url, timeout=5).json()
            lat, lon = data.get(lat_key), data.get(lon_key)
            if lat is not None and lon is not None:
                return lat, lon, data.get(city_key, "your area")
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"couldn't determine location ({last_error})")


def get_current_weather() -> str:
    """Returns a short spoken-friendly weather sentence, or raises on failure."""
    lat, lon, city = _geolocate()

    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        },
        timeout=6,
    )
    resp.raise_for_status()
    cur = resp.json()["current"]
    temp = round(cur["temperature_2m"])
    humidity = round(cur["relative_humidity_2m"])
    wind = round(cur["wind_speed_10m"])
    desc = _describe(cur["weather_code"])

    return (
        f"It's currently {temp} degrees Celsius and {desc} in {city}, "
        f"with {humidity} percent humidity and wind at {wind} kilometers per hour."
    )
