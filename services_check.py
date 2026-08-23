"""
services_check.py - System Services Health & Status Checker
"""
import subprocess
import shutil
import psutil

SERVICES_TO_MONITOR = {
    "Maggie AI": "main.py",
    "Ollama": "ollama",
    "PulseAudio": "pulseaudio",
    "PipeWire": "pipewire",
    "NetworkManager": "NetworkManager",
    "SSH": "ssh",
    "Docker": "docker",
}

def check_service_status(service_name: str, identifier: str) -> str:
    # 1. Systemd Service Check
    if shutil.which("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", identifier],
                capture_output=True,
                text=True,
                timeout=1
            )
            if res.stdout.strip() == "active":
                return "Running"
        except Exception:
            pass

    # 2. Process Table Fallback
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            p_name = proc.info['name'] or ''
            cmdline = " ".join(proc.info['cmdline'] or [])
            if identifier.lower() in p_name.lower() or identifier.lower() in cmdline.lower():
                return "Running"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return "Stopped"

def get_all_services_status() -> dict:
    status_report = {}
    for name, identifier in SERVICES_TO_MONITOR.items():
        status_report[name] = check_service_status(name, identifier)
    return status_report

def get_formatted_services_text() -> str:
    statuses = get_all_services_status()
    lines = ["SERVICES"]
    for service, status in statuses.items():
        symbol = "●" if status == "Running" else "○"
        lines.append(f"{service:<15} {symbol} {status}")
    return "\n".join(lines)
