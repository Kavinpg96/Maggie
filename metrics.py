"""
metrics.py - Complete System Health & Telemetry Collector
"""
import os
import time
import subprocess
import threading
import psutil
import status

def get_top_processes(limit=5):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'memory_percent']):
        try:
            info = p.info
            mem_mb = round((info['memory_info'].rss if info['memory_info'] else 0) / (1024 * 1024), 1)
            procs.append({
                "pid": info['pid'],
                "name": info['name'] or 'unknown',
                "cpu": round(info['cpu_percent'] or 0.0, 1),
                "ram_pct": round(info['memory_percent'] or 0.0, 1),
                "ram_mb": mem_mb
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x['cpu'], reverse=True)
    return procs[:limit]

def ping_host(host):
    try:
        res = subprocess.run(['ping', '-c', '1', '-w', '1', host], capture_output=True, text=True)
        if res.returncode == 0:
            out = res.stdout
            if "time=" in out:
                time_str = out.split("time=")[1].split(" ")[0]
                return f"{float(time_str):.1f} ms"
    except Exception:
        pass
    return "Offline"

def get_detailed_telemetry():
    # CPU
    cpu_overall = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
    try:
        load_avg = [round(x, 2) for x in psutil.getloadavg()]
    except Exception:
        load_avg = [0.0, 0.0, 0.0]

    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk
    disk = psutil.disk_usage('/')

    # Temps
    cpu_temp = 45.0
    try:
        temps = psutil.sensors_temperatures()
        if "coretemp" in temps:
            cpu_temp = temps["coretemp"][0].current
        elif "cpu_thermal" in temps:
            cpu_temp = temps["cpu_thermal"][0].current
    except Exception:
        pass

    # Network
    gateway_ping = ping_host("192.168.1.1")
    google_ping = ping_host("8.8.8.8")

    # Battery
    bat = psutil.sensors_battery()
    battery_pct = round(bat.percent, 1) if bat else 100.0
    charging = bat.power_plugged if bat else True

    return {
        "cpu_pct": cpu_overall,
        "cpu_cores": cpu_cores,
        "load_avg": load_avg,
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_pct": mem.percent,
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_pct": disk.percent,
        "cpu_temp": cpu_temp,
        "ping_gateway": gateway_ping,
        "ping_dns": google_ping,
        "battery_pct": battery_pct,
        "charging": charging,
        "uptime_hrs": round((time.time() - psutil.boot_time()) / 3600, 1),
        "top_processes": get_top_processes(5)
    }

def _telemetry_loop(on_critical_failure):
    while not status.get_flags().get("exit_requested", False):
        try:
            telemetry = get_detailed_telemetry()
            status.set_metrics(**telemetry)
        except Exception:
            pass
        time.sleep(1.5)

def start(on_critical_failure=None):
    threading.Thread(target=_telemetry_loop, args=(on_critical_failure,), daemon=True).start()
