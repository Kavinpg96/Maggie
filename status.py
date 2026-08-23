"""
status.py - Centralized Thread-Safe State & Telemetry Store
"""
import threading

_lock = threading.Lock()

_state = {
    "state": "idle",
    "status": "Online",
    "query": "",
    "answer": "",
    "critical": False,
    "metrics": {
        "cpu_pct": 0,
        "ram_used_gb": 0,
        "ram_total_gb": 0,
        "ram_pct": 0,
        "swap_used_gb": 0,
        "swap_total_gb": 0,
        "disk_used_gb": 0,
        "disk_total_gb": 0,
        "disk_pct": 0,
        "load_avg": [0.0, 0.0, 0.0],
        "cpu_temp": 45.0,
        "battery_pct": 100,
        "charging": True,
        "ping_gateway": "--",
        "ping_dns": "--",
        "top_processes": []
    },
    "flags": {
        "exit_requested": False,
        "muted": False,
        "paused": False,
        "sleeping": False,
    },
    "traffic_map": None
}


def set_status(state: str, message: str = ""):
    with _lock:
        _state["state"] = state
        if message:
            _state["status"] = message


def set_exchange(query: str, answer: str):
    with _lock:
        _state["query"] = query
        _state["answer"] = answer


def set_metrics(**kwargs):
    with _lock:
        _state["metrics"].update(kwargs)


def set_flag(key: str, value: bool):
    with _lock:
        _state["flags"][key] = value


def set_traffic_map(data: dict):
    with _lock:
        _state["traffic_map"] = data


def get_flags() -> dict:
    with _lock:
        return dict(_state["flags"])


def get_status() -> dict:
    with _lock:
        return {
            "state": _state["state"],
            "status": _state["status"],
            "query": _state["query"],
            "answer": _state["answer"],
            "critical": _state["critical"],
            "metrics": dict(_state["metrics"]),
            "flags": dict(_state["flags"]),
            "traffic_map": _state["traffic_map"]
        }
