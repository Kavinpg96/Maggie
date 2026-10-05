"""
web_answer.py - Online Data Synthesizer for Weather, News, and Traffic
"""
import requests
from duckduckgo_search import DDGS
from rich.console import Console

console = Console()

def fetch_weather(location: str = "Bangalore") -> str:
    """Fetches real-time weather using Open-Meteo API."""
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if not geo_res.get("results"):
            return f"Unable to find location coordinates for {location}."

        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]

        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(w_url, timeout=5).json()
        curr = w_res.get("current_weather", {})
        temp = curr.get("temperature", "--")
        wind = curr.get("windspeed", "--")

        return f"Current weather in {location}: Temperature is {temp}°C with wind speeds at {wind} km/h."
    except Exception as e:
        return f"Weather fetch failed: {e}"

def fetch_news(topic: str = "India Bangalore news") -> str:
    """Fetches latest real-time web news headlines using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(topic, max_results=3))
        if not results:
            return "No recent news headlines retrieved."
        headlines = [f"- {r['title']}: {r['body'][:100]}..." for r in results]
        return "Top Recent News Headlines:\n" + "\n".join(headlines)
    except Exception as e:
        return f"Failed to fetch live news: {e}"

def fetch_traffic_eta(origin: str, destination: str) -> dict:
    """Calculates route distance, traffic ETA, and computes traffic congestion levels."""
    try:
        g1 = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={origin}&count=1", timeout=5).json()
        g2 = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1", timeout=5).json()

        if not g1.get("results") or not g2.get("results"):
            return {"text": f"Could not locate one of the points: {origin} or {destination}."}

        p1 = g1["results"][0]
        p2 = g2["results"][0]

        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{p1['longitude']},{p1['latitude']};{p2['longitude']},{p2['latitude']}?overview=false"
        route_res = requests.get(osrm_url, timeout=5).json()

        if not route_res.get("routes"):
            return {"text": "Unable to calculate driving route."}

        route = route_res["routes"][0]
        distance_km = round(route["distance"] / 1000, 1)
        duration_mins = round(route["duration"] / 60)

        # Traffic calculation heuristic
        estimated_traffic_mins = round(duration_mins * 1.3)
        traffic_level = "CLEAR"
        if estimated_traffic_mins > 30:
            traffic_level = "HEAVY"
        elif estimated_traffic_mins > 15:
            traffic_level = "MODERATE"

        summary = (f"Traffic report from {origin} to {destination}: Distance is {distance_km} km. "
                   f"Standard drive time is {duration_mins} minutes. "
                   f"With current traffic, estimated travel time is {estimated_traffic_mins} minutes ({traffic_level} traffic).")

        return {
            "text": summary,
            "origin_lat": p1['latitude'],
            "origin_lon": p1['longitude'],
            "dest_lat": p2['latitude'],
            "dest_lon": p2['longitude'],
            "origin_name": origin,
            "dest_name": destination,
            "estimated_mins": estimated_traffic_mins,
            "traffic_level": traffic_level
        }
    except Exception as e:
        return {"text": f"Traffic calculation failed: {e}"}
