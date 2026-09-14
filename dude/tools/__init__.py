"""
Tools and Automation subsystem for DUDE 0.4.
"""

from dude.tools.registry import ToolRegistry, ToolExecutionError
from dude.tools.system import (
    get_default_registry,
    get_system_stats,
    launch_app,
    open_browser,
    create_note,
    list_notes,
    get_current_time,
    set_timer,
)

__all__ = [
    "ToolRegistry",
    "ToolExecutionError",
    "get_default_registry",
    "get_system_stats",
    "launch_app",
    "open_browser",
    "create_note",
    "list_notes",
    "get_current_time",
    "set_timer",
]
