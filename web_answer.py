"""
web_answer.py - Online Data Synthesizer for Weather, News, Traffic, and Browser Search
"""
import math
import requests
import webbrowser
import urllib.parse
import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
from zoneinfo import ZoneInfo
from duckduckgo_search import DDGS

import applog
from config import TOMTOM_API_KEY

_INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _friendly_error(action: str, e: Exception) -> str:
    """Never speak a raw exception/URL out loud -- log the real detail to
    console for debugging, return a short clean sentence for TTS."""
    detail = str(e)
    applog.log(f"{action} error detail: {detail}", style="red")
    if "ratelimit" in detail.lower() or " 202 " in detail:
        return f"{action} is temporarily rate limited. Please try again in a moment."
    return f"{action} isn't working right now. Please try again shortly."


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
        return _friendly_error("Weather lookup", e)

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
        return _friendly_error("News search", e)


def fetch_world_news(limit: int = 8) -> list[dict]:
    """Fetch recent, source-linked world headlines from the BBC World RSS feed."""
    response = requests.get(
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        headers={"User-Agent": "Maggie-AI/1.0"},
        timeout=10,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    stories = []
    for item in root.findall("./channel/item")[:max(1, min(limit, 12))]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        summary = html.unescape(
            re.sub(r"<[^>]*>", " ", item.findtext("description") or "")
        )
        summary = re.sub(r"\s+", " ", summary).strip()
        if not title or not link.startswith("https://www.bbc.co.uk/"):
            continue
        published = item.findtext("pubDate") or ""
        try:
            published = parsedate_to_datetime(published).isoformat()
        except (TypeError, ValueError, OverflowError):
            published = ""
        stories.append({
            "title": title,
            "summary": summary[:1000],
            "source": "BBC News",
            "published": published,
            "url": link,
        })
    return stories


def elaborate_news_story(story: dict) -> str:
    """Explain a news item using only its linked source headline and summary."""
    title = str(story.get("title", ""))[:300]
    summary = str(story.get("summary", ""))[:1500]
    if not title or not summary:
        raise ValueError("The selected story has no usable source summary.")

    prompt = (
        "Explain this news story in plain language for a general reader. Use only "
        "the headline and source summary below. Explain what is reported and why "
        "it may matter, but do not invent details or present assumptions as facts. "
        "Say when the short source summary does not provide enough detail.\n\n"
        f"Headline: {title}\nSource summary: {summary}"
    )
    from config import GROQ_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL

    if GROQ_API_KEY:
        try:
            from groq import Groq

            response = Groq(api_key=GROQ_API_KEY).chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=350,
            )
            answer = response.choices[0].message.content
            if answer and answer.strip():
                return answer.strip()
        except Exception as exc:
            applog.log(f"News explanation via Groq failed: {exc}", style="yellow")

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=15,
        )
        response.raise_for_status()
        answer = response.json().get("message", {}).get("content", "").strip()
        if answer:
            return answer
    except requests.RequestException as exc:
        applog.log(f"News explanation via local AI failed: {exc}", style="yellow")

    return (
        f"{summary}\n\nThis is the source's available summary. Configure Groq or "
        "a local Ollama model for an AI-generated explanation."
    )


def _open_in_app(url: str, title: str = "Maggie Browser") -> bool:
    """Opens `url` as a second window of Maggie's own pywebview process
    instead of launching external Chrome, so it stays part of the same
    application. Returns False on any failure so the caller can fall
    back to webbrowser.open() -- creating windows from a background
    thread is a known rough edge of pywebview depending on the GUI
    backend (GTK/QT) in use, so this isn't guaranteed on every setup."""
    try:
        import webview
        webview.create_window(title, url, width=1100, height=750)
        return True
    except Exception as e:
        applog.log(f"In-app window failed, falling back to external browser: {e}", style="yellow")
        return False


def open_browser_search(term: str) -> str:
    """Opens a Google search for `term` as an in-app window when possible,
    falling back to the system browser if that fails."""
    term = term.strip(" .?!")
    if not term:
        return "What would you like me to search for?"
    url = "https://www.google.com/search?q=" + urllib.parse.quote(term)

    if _open_in_app(url, f"Search: {term}"):
        return f"Searching for {term}."

    try:
        webbrowser.get("google-chrome").open(url)
    except webbrowser.Error:
        try:
            webbrowser.open(url)  # fall back to whatever the system default browser is
        except Exception as e:
            return _friendly_error("Opening the browser", e)
    return f"Searching Chrome for {term}."


# --- Multi-site / topic-routed fetching ---
# Explicit site names in the query always win over topic guessing.
SITE_NAME_TO_DOMAIN = {
    "imdb": "imdb.com",
    "zomato": "zomato.com",
    "amazon": "amazon.in",
    "flipkart": "flipkart.com",
    "wikipedia": "wikipedia.org",
    "espncricinfo": "espncricinfo.com",
    "techcrunch": "techcrunch.com",
}

# Topic keyword -> the site to check when no explicit site was named.
# Edit/extend this freely as you find topics you ask about often.
TOPIC_TO_DOMAIN = {
    "movie": "imdb.com",
    "movies": "imdb.com",
    "restaurant": "zomato.com",
    "restaurants": "zomato.com",
    "food": "zomato.com",
    "cricket": "espncricinfo.com",
    "recipe": "allrecipes.com",
    "recipes": "allrecipes.com",
}


def fetch_from_domain(query: str, domain: str, max_results: int = 3) -> str:
    """Search DuckDuckGo restricted to one domain (site:domain.com query)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"site:{domain} {query}", max_results=max_results))
        if not results:
            return f"I couldn't find anything on {domain} for {query}."
        lines = [f"- {r['title']}: {r['body'][:120]}..." for r in results]
        return f"From {domain}:\n" + "\n".join(lines)
    except Exception as e:
        return _friendly_error(f"Search on {domain}", e)


def fetch_cross_checked(query: str, max_results: int = 5) -> str:
    """General search that dedupes results by source domain, so the
    answer draws from a few different sites instead of just the top hit."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "I couldn't find anything on that."
        seen_domains = set()
        lines = []
        for r in results:
            domain = urllib.parse.urlparse(r.get("href", "")).netloc or "web"
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            lines.append(f"- ({domain}) {r['title']}: {r['body'][:120]}...")
            if len(lines) >= 3:
                break
        return "\n".join(lines) if lines else "I couldn't find anything on that."
    except Exception as e:
        return _friendly_error("Search", e)


def fetch_topic(query: str) -> str:
    """Routes to a named/implied site when one applies, else cross-checks
    a few general sources. This is the entry point brain.py calls."""
    q = query.lower()

    for name, domain in SITE_NAME_TO_DOMAIN.items():
        if name in q:
            return fetch_from_domain(query, domain)

    for topic, domain in TOPIC_TO_DOMAIN.items():
        if topic in q:
            return fetch_from_domain(query, domain)

    return fetch_cross_checked(query)


def resolve_official_site(name: str) -> str:
    """Finds the likely official site URL for `name` via a live search.
    Used for sites too numerous to hardcode (government/institutional
    sites, etc.) -- SITE_NAME_TO_DOMAIN above is still checked first by
    callers for the common/curated cases."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{name} official website", max_results=1))
        if not results:
            return ""
        return results[0].get("href", "")
    except Exception:
        return ""


def open_official_site(name: str):
    """Resolves and opens `name`'s official site as an in-app window when
    possible, falling back to the system browser if that fails.
    Returns (opened: bool, domain: str, message: str) -- domain is
    returned so callers can immediately search within that same site
    (e.g. for "check for new notifications")."""
    url = resolve_official_site(name)
    if not url:
        return False, "", f"I couldn't find an official site for {name}."

    domain = urllib.parse.urlparse(url).netloc

    if _open_in_app(url, f"{name.title()} — Maggie"):
        return True, domain, f"Opening {name}'s website."

    try:
        webbrowser.get("google-chrome").open(url)
    except webbrowser.Error:
        try:
            webbrowser.open(url)
        except Exception as e:
            return False, domain, _friendly_error(f"Opening {name}'s site", e)
    return True, domain, f"Opening {name}'s website."

def fetch_traffic_eta(origin: str, destination: str) -> dict:
    """Fetch a route with live traffic when TomTom is configured, otherwise route-only."""
    try:
        g1_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": origin, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        g1_response.raise_for_status()
        g1 = g1_response.json()
        g2_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": destination, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        g2_response.raise_for_status()
        g2 = g2_response.json()

        if not g1.get("results") or not g2.get("results"):
            return {"text": f"Could not locate one of the points: {origin} or {destination}."}

        p1 = g1["results"][0]
        p2 = g2["results"][0]

        if TOMTOM_API_KEY:
            locations = (
                f"{p1['latitude']},{p1['longitude']}:"
                f"{p2['latitude']},{p2['longitude']}"
            )
            tomtom_url = (
                "https://api.tomtom.com/routing/1/calculateRoute/"
                f"{locations}/json"
            )
            try:
                response = requests.get(
                    tomtom_url,
                    params={
                        "key": TOMTOM_API_KEY,
                        "traffic": "true",
                        "travelMode": "car",
                        "routeType": "fastest",
                        "computeTravelTimeFor": "all",
                    },
                    timeout=12,
                )
            except requests.RequestException as e:
                applog.log(
                    f"TomTom traffic request failed ({type(e).__name__})",
                    style="red",
                )
                raise RuntimeError("TomTom traffic service could not be reached") from e

            if response.status_code in (401, 403):
                applog.log(
                    f"TomTom traffic API rejected TOMTOM_API_KEY (HTTP {response.status_code})",
                    style="red",
                )
                return {
                    "text": (
                        "TomTom rejected its API key. Check TOMTOM_API_KEY in .env "
                        "and restart Maggie."
                    )
                }
            if response.status_code >= 400:
                raise RuntimeError(
                    f"TomTom traffic API returned HTTP {response.status_code}"
                )

            tomtom_data = response.json()
            if not tomtom_data.get("routes"):
                raise RuntimeError("TomTom did not return a driving route")

            route = tomtom_data["routes"][0]
            route_summary = route["summary"]
            duration_seconds = route_summary["travelTimeInSeconds"]
            delay_seconds = route_summary.get("trafficDelayInSeconds")
            if delay_seconds is None:
                raise RuntimeError("TomTom response did not include live traffic delay")

            duration_mins = round(duration_seconds / 60)
            delay_mins = max(0, round(delay_seconds / 60))
            route_points = [
                [point["longitude"], point["latitude"]]
                for leg in route.get("legs", [])
                for point in leg.get("points", [])
            ]
            distance_km = round(route_summary["lengthInMeters"] / 1000, 1)
            summary = (
                f"TomTom live traffic route from {origin} to {destination}: "
                f"{distance_km} km, about {duration_mins} minutes, "
                f"including approximately {delay_mins} minutes of traffic delay."
            )
            return {
                "text": summary,
                "origin_lat": p1["latitude"],
                "origin_lon": p1["longitude"],
                "dest_lat": p2["latitude"],
                "dest_lon": p2["longitude"],
                "origin_name": origin,
                "dest_name": destination,
                "estimated_mins": duration_mins,
                "traffic_delay_mins": delay_mins,
                "traffic_live": True,
                "route_coordinates": route_points,
            }

        osrm_url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{p1['longitude']},{p1['latitude']};"
            f"{p2['longitude']},{p2['latitude']}"
        )
        route_response = requests.get(
            osrm_url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=10,
        )
        route_response.raise_for_status()
        route_res = route_response.json()

        if not route_res.get("routes"):
            return {"text": "Unable to calculate driving route."}

        route = route_res["routes"][0]
        distance_km = round(route["distance"] / 1000, 1)
        duration_mins = round(route["duration"] / 60)
        route_coordinates = route.get("geometry", {}).get("coordinates", [])
        summary = (
            f"Route from {origin} to {destination}: {distance_km} km, "
            f"about {duration_mins} minutes without live traffic data."
        )

        return {
            "text": summary,
            "origin_lat": p1['latitude'],
            "origin_lon": p1['longitude'],
            "dest_lat": p2['latitude'],
            "dest_lon": p2['longitude'],
            "origin_name": origin,
            "dest_name": destination,
            "estimated_mins": duration_mins,
            "traffic_level": "UNAVAILABLE",
            "traffic_live": False,
            "route_coordinates": route_coordinates,
        }
    except Exception as e:
        return {"text": _friendly_error("Traffic lookup", e)}


def fetch_marathahalli_traffic() -> dict:
    """Fetch the current TomTom flow for the Marathahalli junction road segment."""
    if not TOMTOM_API_KEY:
        return {
            "traffic_live": False,
            "error": "Live traffic needs a TomTom key. Set TOMTOM_API_KEY in .env.",
        }

    try:
        response = requests.get(
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json",
            params={
                "key": TOMTOM_API_KEY,
                "point": "12.9591,77.7010",
                "unit": "KMPH",
            },
            timeout=10,
        )
        if response.status_code in (401, 403):
            return {
                "traffic_live": False,
                "error": "TomTom rejected the traffic key. Check TOMTOM_API_KEY in .env.",
            }
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("TomTom returned an invalid traffic-flow response.")
        segment = payload.get("flowSegmentData")
        if not isinstance(segment, dict):
            raise ValueError("TomTom returned no traffic-flow segment.")

        current_speed = float(segment["currentSpeed"])
        free_flow_speed = float(segment["freeFlowSpeed"])
        current_travel_time = float(segment["currentTravelTime"])
        free_flow_travel_time = float(segment["freeFlowTravelTime"])
        confidence = float(segment.get("confidence", 0))
        measurements = (
            current_speed,
            free_flow_speed,
            current_travel_time,
            free_flow_travel_time,
            confidence,
        )
        if (
            not all(math.isfinite(value) for value in measurements)
            or current_speed < 0
            or current_travel_time < 0
            or free_flow_speed <= 0
            or free_flow_travel_time <= 0
        ):
            raise ValueError("TomTom returned invalid traffic measurements.")

        speed_ratio = current_speed / free_flow_speed
        traffic_level = (
            "Light"
            if speed_ratio >= 0.75
            else "Moderate"
            if speed_ratio >= 0.4
            else "Heavy"
        )
        delay_seconds = max(0, current_travel_time - free_flow_travel_time)
        coordinate_data = segment.get("coordinates")
        coordinates = (
            coordinate_data.get("coordinate", [])
            if isinstance(coordinate_data, dict)
            else []
        )
        if not isinstance(coordinates, list):
            coordinates = []
        road_coordinates = [
            [float(point["latitude"]), float(point["longitude"])]
            for point in coordinates
            if isinstance(point, dict)
            and "latitude" in point
            and "longitude" in point
        ]
        return {
            "traffic_live": True,
            "place": "Marathahalli junction, Bengaluru",
            "latitude": 12.9591,
            "longitude": 77.7010,
            "current_speed_kmh": round(current_speed, 1),
            "free_flow_speed_kmh": round(free_flow_speed, 1),
            "current_travel_time_mins": round(current_travel_time / 60, 1),
            "free_flow_travel_time_mins": round(free_flow_travel_time / 60, 1),
            "traffic_delay_mins": round(delay_seconds / 60, 1),
            "traffic_level": traffic_level,
            "confidence": round(confidence, 2),
            "road_closed": segment.get("roadClosure") is True,
            "road_coordinates": road_coordinates,
            "source_timestamp": segment.get("dateTime"),
            "updated_at": datetime.now(_INDIA_TZ).isoformat(),
            "source": "TomTom Traffic Flow",
        }
    except requests.RequestException as exc:
        applog.log(
            f"Marathahalli traffic request failed ({type(exc).__name__})",
            style="red",
        )
        return {
            "traffic_live": False,
            "error": "TomTom traffic data is temporarily unavailable.",
        }
    except (KeyError, TypeError, ValueError) as exc:
        applog.log(f"Invalid Marathahalli traffic response: {exc}", style="red")
        return {
            "traffic_live": False,
            "error": "TomTom returned unusable traffic data for Marathahalli.",
        }
