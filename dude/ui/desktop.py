"""
Standalone Desktop Application Window Launcher for DUDE.
Launches the FastAPI backend server and opens DUDE in an independent
application window (using Windows Edge/Chrome App Mode or system browser).
"""

import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser
from typing import Optional

import uvicorn  # type: ignore

from dude.config import Config
from dude.core.brain import DudeBrain
from dude.voice.service import VoiceService
from dude.server.app import create_app
from dude.tools.system import get_local_ip


def launch_desktop_window(url: str, app_title: str = "DUDE") -> bool:
    """
    Attempts to launch the URL in standalone application mode
    (borderless, dedicated app window without browser tabs/URL bar).
    """
    if sys.platform == "win32":
        # Check for Microsoft Edge (installed on 100% of modern Windows)
        edge_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            "msedge.exe",
        ]
        for edge in edge_paths:
            if os.path.exists(edge) or edge == "msedge.exe":
                try:
                    subprocess.Popen([
                        edge,
                        f"--app={url}",
                        "--window-size=1180,820",
                        f"--app-id=ProjectDUDE",
                    ])
                    return True
                except Exception:
                    pass

        # Check for Chrome
        chrome_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            "chrome.exe",
        ]
        for chrome in chrome_paths:
            if os.path.exists(chrome) or chrome == "chrome.exe":
                try:
                    subprocess.Popen([
                        chrome,
                        f"--app={url}",
                        "--window-size=1180,820",
                    ])
                    return True
                except Exception:
                    pass

    # Fallback to standard system browser
    return webbrowser.open(url)


class DudeDesktopApp:
    """
    Coordinates the background local server and independent desktop app window.
    """

    def __init__(
        self,
        config: Config,
        brain: Optional[DudeBrain] = None,
        voice: Optional[VoiceService] = None,
    ):
        self.config = config
        self.brain = brain or DudeBrain(config=config)
        self.voice = voice or VoiceService(config=config)
        self.app = create_app(brain=self.brain, voice=self.voice, config=self.config)
        self._server: Optional[uvicorn.Server] = None
        self._server_thread: Optional[threading.Thread] = None

    def start_server_in_background(self) -> None:
        """Starts Uvicorn in a daemon thread."""
        uvicorn_config = uvicorn.Config(
            app=self.app,
            host=self.config.server_host,
            port=self.config.server_port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(uvicorn_config)

        def _run():
            self._server.run()

        self._server_thread = threading.Thread(target=_run, daemon=True)
        self._server_thread.start()

        # Wait briefly for server to bind port
        time.sleep(1.2)

    def run(self, open_window: bool = True) -> None:
        """
        Runs the independent DUDE app:
        1. Starts backend server
        2. Prints connection information (Desktop + Mobile)
        3. Launches standalone desktop app window
        """
        port = self.config.server_port
        local_ip = get_local_ip()
        desktop_url = f"http://localhost:{port}"
        mobile_url = f"http://{local_ip}:{port}"

        print("=" * 60)
        print("  DUDE 0.4 - Standalone Independent Application")
        print("=" * 60)
        print(f"[*] AI Model      : {self.config.model}")
        print(f"[*] Active Memory : {len(self.brain.get_facts())} facts in SQLite")
        print(f"[*] Voice Engine  : Edge-TTS Neural ({self.voice.get_speaker()})")
        print("-" * 60)
        print(f"[*] Desktop App   : {desktop_url}")
        print(f"[*] Mobile Phone  : {mobile_url}  (Open on same Wi-Fi!)")
        print("=" * 60)

        # Start server
        self.start_server_in_background()

        if open_window:
            print("[*] Launching independent DUDE Desktop Window...")
            launch_desktop_window(desktop_url)

        print("\n[+] DUDE is running! Press Ctrl+C in this terminal to exit.\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDUDE: Shutting down standalone app. Goodbye!\n")
            if self._server:
                self._server.should_exit = True
