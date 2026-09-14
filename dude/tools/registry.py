"""
Tool Registry for DUDE 0.4.
Manages tool definitions, OpenAI/Groq compatible schemas, and error-safe execution.
"""

import json
from typing import Callable, Dict, Any, List, Optional


class ToolExecutionError(Exception):
    """Raised when tool execution encounters a fatal error."""
    pass


class ToolRegistry:
    """
    Registry for functions that can be invoked by DUDE via LLM tool/function calling.
    """

    def __init__(self):
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Any],
    ) -> None:
        """
        Registers a tool function with its JSON schema metadata.
        """
        self._tools[name] = func
        self._schemas[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description.strip(),
                "parameters": parameters,
            },
        }

    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        Returns the list of tool schemas formatted for Groq / OpenAI API.
        """
        return list(self._schemas.values())

    def has_tools(self) -> bool:
        """Returns True if at least one tool is registered."""
        return len(self._tools) > 0

    def execute(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """
        Executes a registered tool by name with arguments.
        Returns serialized string result or formatted error description.
        """
        if name not in self._tools:
            return json.dumps({"status": "error", "message": f"Tool '{name}' is not registered."})

        func = self._tools[name]
        args = arguments or {}

        try:
            result = func(**args)
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2, default=str)
            return str(result)
        except TypeError as e:
            return json.dumps({"status": "error", "message": f"Invalid arguments for '{name}': {str(e)}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Error running tool '{name}': {str(e)}"})
