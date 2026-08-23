# Maggie AI — Autonomous Voice & System Assistant

Maggie is an advanced desktop voice assistant featuring real-time hardware telemetry, online data fetching (weather, news, traffic route calculations), 3D HUD visuals with Leaflet maps, and local desktop control.

---

## Capabilities

- **Voice Interface:** Continuous wake-word listening ("Maggie") with soft speech synthesis via `edge-tts`.
- **Live System Telemetry:** Top running process tracking, per-core CPU load, RAM/Swap metrics, disk space, battery status, and ICMP ping latency.
- **Traffic & Map Engine:** Calculates route distance, traffic congestion levels (`CLEAR`, `MODERATE`, `HEAVY`), and updates a high-contrast square map widget in the bottom-right corner.
- **Dynamic Online / Offline Routing:** Seamless fallback between local system commands, DuckDuckGo web searches, and Groq / Llama AI inference.
- **Subsystem Self-Diagnostics:** Automated memory optimization (`gc.collect()`) and self-test logging to `data/logs/maggie_self_test.log`.

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
