"""
gui.py - Webview Bridge & API Controller
"""
import os
import threading
import time
import urllib.parse
import webbrowser
import webview
import status
import services_check
import diagnostics
import applog
import player_state
import weather
import voice_identity
import web_answer
import market_data
from config import TOMTOM_API_KEY

_ASSET_DIR = os.path.join(os.path.dirname(__file__), "gui3d")
_window = None
_geolocation_enabled = False
_geolocation_request_lock = threading.Lock()
_geolocation_request_expires_at = 0.0

class Api:
    def __init__(self):
        self._services_checked_at = 0.0
        self._services_status = {}
        self._news_cache = []
        self._news_cache_expires_at = 0.0
        self._news_lock = threading.Lock()
        self._market_cache = None
        self._market_cache_expires_at = 0.0
        self._market_lock = threading.Lock()
        self._traffic_cache = None
        self._traffic_cache_expires_at = 0.0
        self._traffic_lock = threading.Lock()

    def get_status(self):
        data = status.get_status()
        now = time.monotonic()
        if now - self._services_checked_at >= 10:
            self._services_status = services_check.get_all_services_status()
            self._services_checked_at = now
        data["services"] = dict(self._services_status)
        data["health"] = {
            "ai_engine": "READY",
            "stt": "READY",
            "tts": "READY",
            "mic": "READY",
            "memory": "READY",
            "database": "READY"
        }
        data["ai_info"] = {
            "model": "openai/gpt-oss-120b",
            "backend": "Groq / Local",
            "latency": "0.82 s"
        }
        # Terminal output mirrored into the dashboard log panel.
        data["logs"] = applog.get_recent_logs()
        # Currently-playing YouTube video (embedded panel), if any.
        data["video_embed_url"] = player_state.get_embed_url()
        data["traffic_live_enabled"] = bool(TOMTOM_API_KEY)
        data["flags"]["voice_profile_enrolled"] = voice_identity.is_enrolled()
        return data

    def get_world_news(self, refresh=False):
        with self._news_lock:
            if not refresh and time.monotonic() < self._news_cache_expires_at:
                return {"stories": list(self._news_cache), "cached": True}
            try:
                stories = web_answer.fetch_world_news()
            except Exception as e:
                applog.log(f"World news feed unavailable: {e}", style="red")
                return {"error": "World news is temporarily unavailable. Please refresh shortly."}
            self._news_cache = stories
            self._news_cache_expires_at = time.monotonic() + 900
            return {"stories": list(stories), "cached": False}

    def explain_world_news(self, story_index):
        try:
            index = int(story_index)
        except (TypeError, ValueError):
            return {"error": "Select a valid news story."}
        with self._news_lock:
            if index < 0 or index >= len(self._news_cache):
                return {"error": "That story is no longer available. Refresh the news list."}
            story = dict(self._news_cache[index])
        try:
            explanation = web_answer.elaborate_news_story(story)
        except Exception as e:
            applog.log(f"Could not explain selected world-news story: {e}", style="red")
            return {"error": "Could not explain this story right now. Please try again."}
        return {"title": story["title"], "explanation": explanation, "url": story["url"]}

    def get_market_watchlist(self):
        try:
            return {"symbols": market_data.get_watchlist()}
        except RuntimeError as e:
            applog.log(f"Could not load market watchlist: {e}", style="red")
            return {"error": "Could not load the saved market watchlist."}

    def set_market_watchlist(self, symbols):
        try:
            normalized = market_data.set_watchlist(symbols)
        except (OSError, TypeError, ValueError, RuntimeError) as e:
            applog.log(f"Rejected market watchlist update: {e}", style="red")
            return {"error": str(e)}
        with self._market_lock:
            self._market_cache = None
            self._market_cache_expires_at = 0.0
        return {"symbols": normalized}

    def get_market_snapshot(self):
        with self._market_lock:
            if (
                self._market_cache is not None
                and time.monotonic() < self._market_cache_expires_at
            ):
                return self._market_cache
        try:
            snapshot = market_data.get_market_snapshot()
        except (OSError, RuntimeError, ValueError) as e:
            applog.log(f"Could not load market data: {e}", style="red")
            return {"error": "Market data is temporarily unavailable."}
        with self._market_lock:
            self._market_cache = snapshot
            self._market_cache_expires_at = time.monotonic() + 9
        return snapshot

    def get_marathahalli_traffic(self):
        with self._traffic_lock:
            if (
                self._traffic_cache is not None
                and time.monotonic() < self._traffic_cache_expires_at
            ):
                return dict(self._traffic_cache)
        traffic = web_answer.fetch_marathahalli_traffic()
        with self._traffic_lock:
            self._traffic_cache = traffic
            cache_seconds = 45 if traffic.get("traffic_live") else 15
            self._traffic_cache_expires_at = time.monotonic() + cache_seconds
        return dict(traffic)

    def open_buyhatke_product(self, product_url):
        if not isinstance(product_url, str) or len(product_url.strip()) > 2048:
            return {"error": "Enter one valid HTTPS product URL (up to 2048 characters)."}
        product_url = product_url.strip()
        parsed = urllib.parse.urlsplit(product_url)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return {"error": "Use a complete HTTPS product URL from a retailer."}
        buyhatke_url = (
            product_url
            if parsed.hostname.lower() == "buyhatke.com"
            else f"https://buyhatke.com/{product_url}"
        )
        opened = webbrowser.open(buyhatke_url)
        if not opened:
            applog.log("Could not open the product in Buyhatke.", style="red")
            return {"opened": False, "error": "Buyhatke could not be opened in the browser."}
        return {"opened": True, "url": buyhatke_url}

    def get_current_location(self):
        try:
            return weather.get_current_location()
        except Exception as e:
            applog.log(f"Dashboard location lookup failed: {e}", style="red")
            return {
                "error": (
                    "No accurate device fix is available. IP location is hidden "
                    "because it can report the wrong city."
                )
            }

    def set_device_location(self, latitude, longitude, accuracy_meters=None):
        try:
            return weather.set_device_location(latitude, longitude, accuracy_meters)
        except (TypeError, ValueError) as e:
            applog.log(f"Rejected device location from dashboard: {e}", style="red")
            if "too imprecise" in str(e):
                return {
                    "error": (
                        "Location is too imprecise for GPS-level results. "
                        "No accurate GNSS fix is available."
                    )
                }
            return {"error": str(e)}

    def request_device_location(self):
        if not _geolocation_enabled:
            return {"error": "Device location is unavailable in this WebView."}
        global _geolocation_request_expires_at
        with _geolocation_request_lock:
            _geolocation_request_expires_at = time.monotonic() + 10
        return {"ready": True}

    def open_google_maps(self):
        try:
            location = weather.get_current_location()
            query = f"{location['latitude']},{location['longitude']}"
            url = "https://www.google.com/maps/search/?" + urllib.parse.urlencode(
                {"api": "1", "query": query}
            )
        except RuntimeError:
            return {
                "opened": False,
                "error": "Find and verify a device location before opening it in Google Maps.",
            }

        opened = webbrowser.open(url)
        if not opened:
            applog.log("Could not open Google Maps in the default browser.", style="red")
        return {"opened": bool(opened), "url": url}

    def open_google_maps_route(self):
        traffic = status.get_status().get("traffic_map")
        if not traffic:
            return {"error": "Ask Maggie for a route first."}

        url = "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(
            {
                "api": "1",
                "origin": traffic["origin_name"],
                "destination": traffic["dest_name"],
                "travelmode": "driving",
            }
        )
        opened = webbrowser.open(url)
        if not opened:
            applog.log("Could not open Google Maps directions.", style="red")
        return {"opened": bool(opened), "url": url}


def _enable_user_requested_geolocation():
    """Allow Qt WebEngine geolocation only for the local dashboard page."""
    global _geolocation_enabled
    try:
        from webview.platforms import qt as qt_backend

        page_class = qt_backend.BrowserView.WebPage
        original_handler = page_class.onFeaturePermissionRequested
        if getattr(original_handler, "_maggie_geolocation_handler", False):
            _geolocation_enabled = True
            return

        def on_feature_permission_requested(page, url, feature):
            if feature == qt_backend.QWebPage.Feature.Geolocation and url.scheme() == "file":
                from PyQt6.QtWebEngineCore import QWebEnginePage

                global _geolocation_request_expires_at
                with _geolocation_request_lock:
                    requested_by_user = time.monotonic() <= _geolocation_request_expires_at
                    _geolocation_request_expires_at = 0.0
                permission = (
                    QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
                    if requested_by_user
                    else QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
                )
                page.setFeaturePermission(url, feature, permission)
                return
            original_handler(page, url, feature)

        on_feature_permission_requested._maggie_geolocation_handler = True
        page_class.onFeaturePermissionRequested = on_feature_permission_requested
        _geolocation_enabled = True
    except (ImportError, AttributeError) as e:
        _geolocation_enabled = False
        applog.log(
            f"Device geolocation is unavailable in this WebView; using IP estimate: {e}",
            style="yellow",
        )


def close_window():
    global _window
    if _window:
        try:
            _window.destroy()
        except Exception:
            pass

def run():
    global _window
    _enable_user_requested_geolocation()
    index_path = os.path.join(_ASSET_DIR, "index.html")
    api = Api()
    _window = webview.create_window(
        "MAGGIE INTELLIGENCE DASHBOARD", url=index_path, js_api=api,
        fullscreen=True, background_color="#020609"
    )
    # GTK/gi is not installed in the supported Linux setup; select Qt directly
    # so pywebview does not probe GTK and trigger GLib/Pango initialization.
    webview.start(debug=False, gui="qt")
