"""
Free, no-API-key weather lookup.
1. Weather lookup may use an approximate location from IP; it is not used
   as Maggie's answer to "where am I".
2. Current weather for that location from Open-Meteo (free, no key).
"""
import math
import threading
import time
import requests

_device_location_lock = threading.Lock()
_device_location = None
_MAX_DEVICE_LOCATION_ACCURACY_METERS = 100
_DEVICE_LOCATION_MAX_AGE_SECONDS = 300

_WEATHER_CODES = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow", 73: "snow",
    75: "heavy snow", 80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "severe thunderstorms",
}


def _describe(code: int) -> str:
    return _WEATHER_CODES.get(code, "unusual weather")


def get_current_location() -> dict:
    """Return a verified device fix; never mistake IP geolocation for current location."""
    global _device_location

    with _device_location_lock:
        if _device_location is not None:
            if time.time() - _device_location["captured_at"] <= _DEVICE_LOCATION_MAX_AGE_SECONDS:
                return dict(_device_location)
            _device_location = None

    raise RuntimeError(
        "No verified device location is available. IP-based location was disabled "
        "because it can identify the wrong city."
    )


def set_device_location(latitude, longitude, accuracy_meters=None) -> dict:
    """Cache coordinates received after the user enables device location."""
    global _device_location

    latitude = float(latitude)
    longitude = float(longitude)
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        raise ValueError("location coordinates must be finite numbers")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("location coordinates are outside valid ranges")

    if accuracy_meters is not None:
        accuracy_meters = float(accuracy_meters)
        if not math.isfinite(accuracy_meters) or accuracy_meters < 0:
            raise ValueError("location accuracy must be a non-negative number")
        if accuracy_meters > _MAX_DEVICE_LOCATION_ACCURACY_METERS:
            raise ValueError(
                "device location is too imprecise "
                f"(reported accuracy ±{round(accuracy_meters)} m)"
            )
    else:
        raise ValueError("the device did not report location accuracy")

    place = f"{latitude:.5f}, {longitude:.5f}"
    accuracy = f"browser/OS location fix (reported accuracy ±{round(accuracy_meters)} m)"

    location = {
        "latitude": latitude,
        "longitude": longitude,
        "place": place,
        "accuracy": accuracy,
        "accuracy_meters": accuracy_meters,
        "source": "device",
        "captured_at": time.time(),
    }
    with _device_location_lock:
        _device_location = location
    return dict(location)


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
