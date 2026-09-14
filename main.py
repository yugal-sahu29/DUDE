#!/usr/bin/env python3
"""
DUDE 0.1 - Main Application Entry Point
Starts the terminal chat session with DUDE.
"""

import sys

# Ensure UTF-8 encoding on Windows consoles to support emojis cleanly
if sys.platform == "win32":
    try:
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dude.config import Config, ConfigurationError
from dude.core.brain import DudeBrain
from dude.ui.terminal import DudeTerminalUI
from dude.ui.desktop import DudeDesktopApp
from dude.server.app import create_app

# Top-level ASGI FastAPI instance for Vercel, Uvicorn, and cloud deployments
app = create_app()


def main() -> None:
    """Initializes and runs the DUDE application."""
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("DUDE 0.4 - Personal AI Assistant")
        print("Usage:")
        print("  python main.py               # Launch Standalone Desktop App (Default)")
        print("  python main.py --cli         # Run Terminal CLI Chat Mode")
        print("  python main.py --server-only # Run Headless Server Mode (for phone/PWA)")
        print("  python main.py --help        # Show this help message")
        sys.exit(0)

    try:
        # Load and validate configuration
        config = Config.load()
    except ConfigurationError as err:
        print("\n" + "=" * 55)
        print("  [!] DUDE Configuration Notice")
        print("=" * 55)
        print(f"\n{err}\n")
        print("=" * 55 + "\n")
        sys.exit(1)
    except Exception as err:
        print(f"\n[!] Unexpected error loading configuration: {err}\n")
        sys.exit(1)

    try:
        if "--cli" in args or "-c" in args:
            # Terminal CLI Mode
            brain = DudeBrain(config=config)
            ui = DudeTerminalUI(brain=brain)
            ui.run()
        else:
            # Standalone Desktop Application (Default)
            open_window = "--server-only" not in args and "-s" not in args
            app = DudeDesktopApp(config=config)
            app.run(open_window=open_window)
    except Exception as err:
        print(f"\n[!] Fatal application error: {err}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
