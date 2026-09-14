"""
System Automation Tools for DUDE 0.4.
Provides hardware telemetry, application launching, browser/web search,
desktop notes, real-time clock, and countdown timers.
"""

import os
import re
import sys
import time
import datetime
import platform
import threading
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List

import psutil  # type: ignore

from dude.tools.registry import ToolRegistry

# Local directory for saving notes
NOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "notes"


# ----------------------------------------------------------------------
# Tool Implementations & Utilities
# ----------------------------------------------------------------------

def get_local_ip() -> str:
    """Finds the local network IPv4 address for phone connectivity."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_system_stats() -> Dict[str, Any]:
    """
    Gathers real-time hardware telemetry: CPU load, RAM usage, Battery status,
    Disk space, and system uptime.
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)

        # Memory (RAM)
        mem = psutil.virtual_memory()
        total_ram_gb = round(mem.total / (1024 ** 3), 1)
        used_ram_gb = round(mem.used / (1024 ** 3), 1)
        ram_percent = mem.percent

        # Disk
        disk_path = "C:\\" if sys.platform == "win32" else "/"
        disk = psutil.disk_usage(disk_path)
        total_disk_gb = round(disk.total / (1024 ** 3), 1)
        free_disk_gb = round(disk.free / (1024 ** 3), 1)
        disk_percent = disk.percent

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            battery_info = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "charging_status": "Plugged in / Charging" if battery.power_plugged else "Running on Battery",
            }
        else:
            battery_info = {"status": "Desktop / No battery detected"}

        # Uptime
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime_str = str(datetime.datetime.now() - boot_time).split(".")[0]

        return {
            "status": "success",
            "os": f"{platform.system()} {platform.release()}",
            "cpu": {
                "usage_percent": f"{cpu_percent}%",
                "cores": cpu_count,
            },
            "memory": {
                "total_gb": total_ram_gb,
                "used_gb": used_ram_gb,
                "usage_percent": f"{ram_percent}%",
            },
            "disk": {
                "total_gb": total_disk_gb,
                "free_gb": free_disk_gb,
                "usage_percent": f"{disk_percent}%",
            },
            "battery": battery_info,
            "uptime": uptime_str,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to retrieve system statistics: {str(e)}"}


# Known common Windows application commands/aliases
APP_ALIASES = {
    "notepad": "notepad.exe",
    "notes": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "cmd": "cmd.exe",
    "terminal": "powershell.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "vscode": "code",
    "code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "spotify": "spotify",
    "settings": "ms-settings:",
}


def launch_app(app_name: str) -> Dict[str, Any]:
    """
    Launches a local desktop application on Windows.
    """
    clean_name = app_name.strip().lower()
    target = APP_ALIASES.get(clean_name, app_name.strip())

    try:
        if sys.platform == "win32":
            if target.startswith("ms-settings:"):
                os.startfile(target)
            else:
                subprocess.Popen(target, shell=True)
        else:
            subprocess.Popen([target])

        return {
            "status": "success",
            "app": app_name,
            "message": f"Application '{app_name}' has been launched.",
        }
    except Exception as e:
        return {
            "status": "error",
            "app": app_name,
            "message": f"Could not launch '{app_name}': {str(e)}",
        }


def open_browser(url: Optional[str] = None, search_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Opens a website URL or initiates a web search in the user's default browser.
    """
    try:
        if search_query and not url:
            sq = search_query.strip()
            # If search is for YouTube specifically
            if re.search(r'\byoutube\b', sq, re.IGNORECASE):
                clean_query = re.sub(r'\b(?:search\s+on\s+youtube|on\s+youtube|youtube)\b', '', sq, flags=re.IGNORECASE).strip()
                target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_query or sq)}"
                label = f"YouTube search for '{clean_query or sq}'"
            else:
                clean_query = re.sub(r'\b(?:search\s+(?:for|google\s+for)?|google)\b', '', sq, flags=re.IGNORECASE).strip()
                target_url = f"https://www.google.com/search?q={urllib.parse.quote(clean_query or sq)}"
                label = f"Google search for '{clean_query or sq}'"
        elif url:
            target_url = url.strip()
            if not target_url.startswith(("http://", "https://")):
                target_url = f"https://{target_url}"
            label = target_url
        else:
            target_url = "https://www.google.com"
            label = "default homepage"

        webbrowser.open(target_url)
        return {
            "status": "success",
            "url": target_url,
            "message": f"Opened {label} in your web browser.",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to open browser: {str(e)}"}


def create_note(title: str, content: str) -> Dict[str, Any]:
    """
    Saves a text note into the local notes folder (data/notes/).
    """
    clean_title = re.sub(r'[\\/*?:"<>|]', '_', title.strip())
    if not clean_title:
        clean_title = f"note_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = NOTES_DIR / f"{clean_title}.txt"

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"--- Note: {title} ---\nCreated: {timestamp}\n\n{content.strip()}\n"

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body)
        return {
            "status": "success",
            "title": title,
            "path": str(file_path),
            "message": f"Note '{title}' saved successfully.",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to save note: {str(e)}"}


def list_notes() -> Dict[str, Any]:
    """
    Lists all notes saved in data/notes/.
    """
    if not NOTES_DIR.exists():
        return {"status": "success", "count": 0, "notes": [], "message": "No notes found."}

    notes = []
    for file in NOTES_DIR.glob("*.txt"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            notes.append({
                "name": file.stem,
                "preview": content[:120].replace("\n", " ") + "...",
                "modified": datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
        except Exception:
            continue

    return {
        "status": "success",
        "count": len(notes),
        "notes": notes,
    }


def get_current_time(timezone: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns the current local date, time, weekday, and timezone.
    """
    now = datetime.datetime.now()
    return {
        "status": "success",
        "time": now.strftime("%I:%M:%S %p"),
        "date": now.strftime("%B %d, %Y"),
        "weekday": now.strftime("%A"),
        "iso_timestamp": now.isoformat(),
    }


def set_timer(seconds: int, label: Optional[str] = "Timer") -> Dict[str, Any]:
    """
    Starts a non-blocking background countdown timer for the specified seconds.
    """
    timer_label = label or "Timer"
    if seconds <= 0:
        return {"status": "error", "message": "Timer duration must be greater than 0 seconds."}

    def _timer_callback():
        print(f"\n\n[TIMER ALERT] Time's up for: {timer_label}! ({seconds} seconds elapsed)\a\n")

    t = threading.Timer(float(seconds), _timer_callback)
    t.daemon = True
    t.start()

    return {
        "status": "started",
        "seconds": seconds,
        "label": timer_label,
        "message": f"Timer set for {seconds} seconds ('{timer_label}'). I'll alert you when it finishes!",
    }


# ----------------------------------------------------------------------
# Registry Factory
# ----------------------------------------------------------------------

def get_default_registry() -> ToolRegistry:
    """
    Creates and populates a ToolRegistry with all standard DUDE system tools.
    """
    registry = ToolRegistry()

    # 1. System Telemetry
    registry.register(
        name="get_system_stats",
        description="Inspects real-time hardware telemetry: CPU usage percentage, RAM memory used/free, battery level, disk space, and system uptime.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        func=get_system_stats,
    )

    # 2. Launch Application
    registry.register(
        name="launch_app",
        description="Launches a desktop application on Windows (e.g. notepad, calculator, paint, vs code, spotify, explorer, cmd, chrome, edge, settings).",
        parameters={
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to launch (e.g. 'notepad', 'calculator', 'code', 'spotify').",
                },
            },
            "required": ["app_name"],
        },
        func=launch_app,
    )

    # 3. Open Browser / Web Search
    registry.register(
        name="open_browser",
        description="Opens a website URL in the user's default browser or performs a Google / YouTube search.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to (e.g. 'github.com', 'https://reddit.com').",
                },
                "search_query": {
                    "type": "string",
                    "description": "A search query to look up on Google or YouTube (e.g. 'latest AI news', 'Lo-Fi chill beats on YouTube').",
                },
            },
            "required": [],
        },
        func=open_browser,
    )

    # 4. Create Note
    registry.register(
        name="create_note",
        description="Creates and saves a persistent text note in the local notes directory.",
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the note (e.g. 'Shopping List', 'Ideas').",
                },
                "content": {
                    "type": "string",
                    "description": "The body text content of the note.",
                },
            },
            "required": ["title", "content"],
        },
        func=create_note,
    )

    # 5. List Notes
    registry.register(
        name="list_notes",
        description="Lists all saved local notes and their previews.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        func=list_notes,
    )

    # 6. Current Time
    registry.register(
        name="get_current_time",
        description="Retrieves the current date, time, weekday, and timestamp.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        func=get_current_time,
    )

    # 7. Countdown Timer
    registry.register(
        name="set_timer",
        description="Sets a background countdown timer for a specified number of seconds with a label.",
        parameters={
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "Duration of the countdown in seconds (e.g. 60 for 1 minute, 300 for 5 minutes).",
                },
                "label": {
                    "type": "string",
                    "description": "Label or description for the timer (e.g. 'Tea', 'Break', 'Meeting').",
                },
            },
            "required": ["seconds"],
        },
        func=set_timer,
    )

    return registry
