"""
Unit tests for DUDE 0.4 System Tools & Automation subsystem.
Covers ToolRegistry, System Tools (Stats, App launcher, Notes, Timer),
and autonomous function calling in DudeBrain.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from dude.config import Config
from dude.core.brain import DudeBrain
from dude.tools.registry import ToolRegistry
from dude.tools.system import (
    get_system_stats,
    launch_app,
    open_browser,
    create_note,
    list_notes,
    get_current_time,
    set_timer,
    get_default_registry,
)


class TestDudeTools(unittest.TestCase):
    """Test suite for DUDE system tools and autonomous tool calling."""

    def setUp(self):
        self.config = Config(
            api_key="gsk_test_tool_api_key",
            model="qwen/qwen3.8-27b",
            temperature=0.7,
            max_tokens=500,
            voice_enabled=False,
        )

    def test_registry_registration_and_schemas(self):
        """Verifies tool registration and Groq/OpenAI schema formatting."""
        registry = ToolRegistry()

        def dummy_tool(x: int, y: int) -> int:
            return x + y

        registry.register(
            name="add_numbers",
            description="Adds two integers together",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                },
                "required": ["x", "y"],
            },
            func=dummy_tool,
        )

        self.assertTrue(registry.has_tools())
        schemas = registry.get_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["type"], "function")
        self.assertEqual(schemas[0]["function"]["name"], "add_numbers")
        self.assertIn("Adds two integers", schemas[0]["function"]["description"])

    def test_registry_execute_success(self):
        """Verifies successful tool execution with arguments."""
        registry = ToolRegistry()
        registry.register(
            name="greet",
            description="Greets a user",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}},
            func=lambda name: f"Hello, {name}!",
        )

        result = registry.execute("greet", {"name": "Yugal"})
        self.assertEqual(result, "Hello, Yugal!")

    def test_registry_execute_error_isolation(self):
        """Verifies tool errors return descriptive JSON rather than raising exceptions."""
        registry = ToolRegistry()

        def failing_tool():
            raise ValueError("Something went wrong inside the tool")

        registry.register("failing_tool", "Always fails", {}, failing_tool)

        # Unknown tool
        unknown_res = json.loads(registry.execute("unknown_tool", {}))
        self.assertEqual(unknown_res["status"], "error")
        self.assertIn("not registered", unknown_res["message"])

        # Tool that raises exception
        fail_res = json.loads(registry.execute("failing_tool", {}))
        self.assertEqual(fail_res["status"], "error")
        self.assertIn("Something went wrong", fail_res["message"])

    def test_system_stats(self):
        """Verifies get_system_stats gathers hardware telemetry."""
        stats = get_system_stats()
        self.assertEqual(stats["status"], "success")
        self.assertIn("cpu", stats)
        self.assertIn("memory", stats)
        self.assertIn("disk", stats)
        self.assertIn("uptime", stats)

    @patch("dude.tools.system.subprocess.Popen")
    def test_launch_app_alias(self, mock_popen):
        """Verifies application launcher maps known aliases correctly."""
        result = launch_app("calculator")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["app"], "calculator")
        mock_popen.assert_called_once()

    @patch("dude.tools.system.webbrowser.open")
    def test_open_browser_search(self, mock_webopen):
        """Verifies browser launcher handles search queries."""
        result = open_browser(search_query="quantum computing")
        self.assertEqual(result["status"], "success")
        self.assertIn("Google search", result["message"])
        mock_webopen.assert_called_once()

    def test_notes_creation_and_listing(self):
        """Verifies notes can be created and retrieved."""
        title = "test_system_note_unit"
        content = "Buy groceries and finish Level 3"

        create_res = create_note(title, content)
        self.assertEqual(create_res["status"], "success")

        list_res = list_notes()
        self.assertEqual(list_res["status"], "success")
        note_names = [n["name"] for n in list_res["notes"]]
        self.assertIn(title, note_names)

    def test_get_current_time(self):
        """Verifies real-time clock tool output."""
        time_info = get_current_time()
        self.assertEqual(time_info["status"], "success")
        self.assertIn("time", time_info)
        self.assertIn("date", time_info)
        self.assertIn("weekday", time_info)

    def test_set_timer(self):
        """Verifies timer tool initialization."""
        timer_res = set_timer(10, label="Meeting")
        self.assertEqual(timer_res["status"], "started")
        self.assertEqual(timer_res["seconds"], 10)
        self.assertEqual(timer_res["label"], "Meeting")

    def test_default_registry_has_all_tools(self):
        """Verifies default registry registers all 7 standard tools."""
        registry = get_default_registry()
        schemas = registry.get_schemas()
        tool_names = [s["function"]["name"] for s in schemas]

        expected = [
            "get_system_stats",
            "launch_app",
            "open_browser",
            "create_note",
            "list_notes",
            "get_current_time",
            "set_timer",
        ]
        for t in expected:
            self.assertIn(t, tool_names)

    def test_brain_autonomous_tool_calling(self):
        """Verifies DudeBrain autonomous tool execution loop with Groq tool_calls."""
        mock_memory = MagicMock()
        mock_memory.format_facts_for_prompt.return_value = ""
        mock_memory.auto_extract_facts.return_value = []

        # Setup mock tool registry
        registry = ToolRegistry()
        registry.register(
            name="get_time",
            description="Get current time",
            parameters={"type": "object", "properties": {}},
            func=lambda: "10:30 AM",
        )

        brain = DudeBrain(
            config=self.config,
            memory=mock_memory,
            tools=registry,
        )

        # Mock Groq client responses:
        # First turn: returns tool_calls
        # Second turn: returns final text answer
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_abc_123"
        mock_tool_call.function.name = "get_time"
        mock_tool_call.function.arguments = "{}"

        first_message = MagicMock()
        first_message.tool_calls = [mock_tool_call]
        first_message.content = None

        first_choice = MagicMock()
        first_choice.message = first_message
        first_response = MagicMock()
        first_response.choices = [first_choice]

        second_message = MagicMock()
        second_message.tool_calls = None
        second_message.content = "The time is 10:30 AM."

        second_choice = MagicMock()
        second_choice.message = second_message
        second_response = MagicMock()
        second_response.choices = [second_choice]

        brain.client.chat.completions.create = MagicMock(
            side_effect=[first_response, second_response]
        )

        reply = brain.generate_response("What time is it?")
        self.assertEqual(reply, "The time is 10:30 AM.")
        self.assertEqual(brain.client.chat.completions.create.call_count, 2)


if __name__ == "__main__":
    unittest.main()
