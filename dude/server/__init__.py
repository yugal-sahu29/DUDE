"""
Independent Server Package for DUDE.
Provides FastAPI REST and WebSocket services for the standalone client application.
"""

from dude.server.app import create_app

__all__ = ["create_app"]
