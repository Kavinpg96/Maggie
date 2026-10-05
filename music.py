"""
music.py — YouTube audio search & playback for Maggie

Streams audio directly (no download to disk) using yt-dlp + mpv.
mpv is used instead of vlc/ffplay because it accepts a yt-dlp format
string directly and starts playback fast without buffering a full file.

Setup:
    pip install yt-dlp
    sudo apt install mpv
"""

import subprocess
import shutil

import yt_dlp

import applog
import player_state

_PLAYER_TAG = "maggie-music"  # marks our mpv process so stop() only kills ours


def _mpv_available():
    return shutil.which("mpv") is not None


def search_youtube(query, max_results=1):
    """Search YouTube, return a list of (title, url) tuples. Empty list on failure."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": f"ytsearch{max_results}",
        "noplaylist": True,
        "extract_flat": "in_playlist",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries") or []
            return [
                (e.get("title", "Unknown title"), f"https://www.youtube.com/watch?v={e.get('id')}")
                for e in entries
                if e.get("id")
            ]
    except Exception as exc:
        print(f"[music] search failed: {exc}")
        return []


def play(query, speak_fn=None):
    """
    Search YouTube for `query` and stream the first result via mpv.
    speak_fn: optional callable(str) so Maggie can say status out loud
              (falls back to print if not given).
    Returns True if playback started, False otherwise.
    """
    def say(msg):
        applog.log(msg)
        if speak_fn:
            speak_fn(msg)

    if not _mpv_available():
        say("mpv isn't installed, so I can't play audio. Run: sudo apt install mpv")
        return False

    say(f"Searching YouTube for {query}")
    results = search_youtube(query)
    if not results:
        say(f"I couldn't find anything for {query}")
        return False

    title, url = results[0]
    say(f"Playing {title}")

    try:
        stop()  # don't stack multiple songs
        subprocess.Popen(
            [
                "mpv",
                "--no-video",
                "--ytdl-format=bestaudio",
                "--really-quiet",
                f"--title={_PLAYER_TAG}",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        say("mpv isn't installed, so I can't play audio.")
        return False
    except Exception as exc:
        say(f"Something went wrong trying to play that: {exc}")
        return False


def play_video(query, speak_fn=None):
    """
    Search YouTube for `query` and play it embedded in Maggie's own GUI
    dashboard panel (see player_state.py + gui3d/index.html), instead of
    opening a separate Chrome window.
    """
    import re as _re

    def say(msg):
        applog.log(msg)
        if speak_fn:
            speak_fn(msg)

    say(f"Searching YouTube for {query}")
    results = search_youtube(query)
    if not results:
        say(f"I couldn't find anything for {query}")
        return False

    title, url = results[0]
    match = _re.search(r"v=([\w-]+)", url)
    if not match:
        say(f"Found {title} but couldn't get a playable link for it.")
        return False

    player_state.set_video(match.group(1))
    say(f"Playing {title} on the dashboard.")
    return True


def stop():
    """Kill any Maggie-started mpv playback and clear the GUI video panel."""
    try:
        subprocess.run(["pkill", "-f", f"title={_PLAYER_TAG}"], check=False)
    except Exception:
        pass
    player_state.clear_video()


if __name__ == "__main__":
    # quick manual test: python music.py "song name"
    import sys
    play(" ".join(sys.argv[1:]) or "lofi hip hop radio")
