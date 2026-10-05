# Maggie AI — Autonomous Voice & System Assistant

Maggie is a desktop voice assistant featuring real-time hardware telemetry, online data fetching (weather, news, traffic route calculations), Google Maps links, and local desktop control.

---

## Capabilities

- **Voice Interface:** Continuous wake-word listening ("Maggie") with soft speech synthesis via `edge-tts`.
- **Live System Telemetry:** Top running process tracking, per-core CPU load, RAM/Swap metrics, disk space, battery status, and ICMP ping latency.
- **Traffic & Maps:** A pinned dashboard map stays centered on the Marathahalli junction in Bengaluru and displays TomTom live road speed, free-flow speed, travel time, and delay when `TOMTOM_API_KEY` is configured. Location discovery and Google Maps directions remain available separately.
- **Dynamic Online / Offline Routing:** Seamless fallback between local system commands, DuckDuckGo web searches, and Groq / Llama AI inference.
- **Subsystem Self-Diagnostics:** Automated memory optimization (`gc.collect()`) and self-test logging to `data/logs/maggie_self_test.log`.
- **Persistent conversation memory:** User/assistant turns are stored locally in `data/memory/maggie_memory.db`; recent turns are used for follow-ups.
- **Owner voice indicator:** Say “Maggie, learn my voice” and record five short samples to create an optional local voice profile. Maggie stores derived acoustic features under `~/.local/share/maggie_ai/`; the temporary recordings are discarded. Similarity matching is probabilistic and is not secure authentication or a gate for sensitive actions.
- **World news widget:** The dashboard shows recent BBC World RSS headlines with publication times and source links. Select a headline to request an AI explanation; the explanation is grounded in the source summary. News is cached for 15 minutes, and an AI provider is needed for elaboration beyond the source summary.
- **Market and product widgets:** A pinned NSE/BSE panel shows actual source prices and a labeled five-minute trend estimate, refreshed every ten seconds. With no saved watchlist, it starts with the Nifty 50 (`^NSEI`) and Sensex (`^BSESN`); add up to four indices or `.NS`/`.BO` symbols. Yahoo Finance's public chart endpoint supplies one-minute candles that may be delayed or rate-limited. The estimate is not a price forecast or investment advice. News, location, and product details share a responsive widget panel. The product panel opens an HTTPS retailer URL through Buyhatke; Buyhatke does not expose a public product-data feed here, so its price history is shown on its own page rather than presented as in-dashboard data.
- **Speech capture:** The listener allows longer pauses and utterances before submission. Speech is transcribed by Google's online recognition service, so network quality, microphone quality, language, and room noise can still affect accuracy.

### Run from a terminal (system Python)

Maggie can run without activating a project virtual environment:

```bash
cd /path/to/Maggie_AI
/usr/bin/python3 main.py
```

The required Python packages must be installed for `/usr/bin/python3`; see
`requirements.txt`. Keep the virtual-environment folders out of the launch
command so the terminal always uses the system interpreter.

Conversation history remains in the local SQLite database. When Groq is
configured, Maggie sends the current request and up to 12 recent turns to Groq
to answer follow-ups; avoid sharing information you do not want sent to that
provider.

### Location and traffic setup

Maggie does not present IP-derived locations as your current location. Click
**Find my location** to request a fresh browser/OS fix (the request times out
after eight seconds). Fixes with reported accuracy worse than 100 m are
rejected; accepted fixes are held in memory for up to five minutes and their
reported accuracy is shown. Browser/OS location can still be Wi-Fi/network-
derived and is not guaranteed to be GPS. This computer has no detected GPS
receiver, so true satellite accuracy requires connecting a compatible GNSS
receiver and enabling it in the OS.

**Open Google Maps** first requests a fresh device fix and opens Maps centered
on the verified coordinates. If no sufficiently accurate fix is available,
Maggie reports that instead of opening Maps with an unrelated/default
location. The dashboard keeps the Marathahalli map and market watch visible
while the news, location, and product widgets share a separate panel that
switches every ten seconds and can be selected manually. Hover the panel to
pause its timer. On smaller windows, telemetry panels become horizontally
scrollable and the traffic, market, and rotating widgets reflow into a
scrollable layout to avoid covering one another.

For live traffic-aware routes, add a TomTom developer key to `.env`:

```dotenv
TOMTOM_API_KEY=your_tomtom_key
```

The pinned Marathahalli map remains visible without a key, but live flow values
are explicitly marked unavailable until TomTom is configured. The map uses
OpenStreetMap tiles; live speed, free-flow speed, road travel time, and delay
come from TomTom's nearest traffic-flow segment and refresh about once a
minute. Traffic coverage and confidence depend on the provider.

Ask for a route with both endpoints, for example: “traffic from Chennai to
Tambaram.” Without the key, Maggie draws the road route and reports the
baseline driving-time estimate without claiming live congestion data.

### Speech playback on Linux

Maggie's Edge-TTS audio needs an MP3 player installed on Linux. Install one if
speech is logged but not audible:

```bash
sudo apt install mpg123
```

Maggie also supports `ffplay` or `mpv` when either is already installed.

---

## Directory Structure

```text
Maggie_AI/
├── main.py             # Master process controller & thread manager
├── brain.py            # Conversational intent router & web fallback engine
├── listener.py         # Speech recognition input engine
├── speaker.py          # Edge-TTS text-to-speech audio output
├── metrics.py          # System hardware & process telemetry collector
├── web_answer.py       # Online weather, news, and OSRM traffic ETA calculator
├── diagnostics.py      # Self-test diagnostic logger
├── services_check.py   # Linux daemon status checker
├── memory.py           # SQLite database store
├── status.py           # Thread-safe central state store
├── config.py           # Central system configuration
└── gui3d/
    └── index.html      # Holographic 3D Arc Reactor & Traffic Dashboard
