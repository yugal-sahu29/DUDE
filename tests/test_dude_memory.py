"""
Unit tests for DUDE Level 2: Persistent Memory.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dude.config import Config
from dude.core.brain import DudeBrain
from dude.memory.database import MemoryDatabase
from dude.memory.manager import MemoryManager


class TestDudeMemory(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test databases
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.test_dir.name) / "test_memory.db"
        self.db = MemoryDatabase(db_path=self.db_path)
        self.memory = MemoryManager(db=self.db)
        self.config = Config(api_key="gsk_test_dummy_key", model="qwen/qwen3.8-27b")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_database_initialization(self):
        """Verifies tables are created in SQLite."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row["name"] for row in cursor.fetchall()}
            self.assertIn("facts", tables)
            self.assertIn("sessions", tables)
            self.assertIn("messages", tables)

    def test_fact_management(self):
        """Tests adding, retrieving, formatting, and deleting facts."""
        fact_id = self.memory.add_fact("My favorite language is Python", fact_key="programming")
        self.assertGreater(fact_id, 0)

        # Duplicate fact should return existing ID
        dup_id = self.memory.add_fact("My favorite language is Python")
        self.assertEqual(fact_id, dup_id)

        # Retrieve facts
        facts = self.memory.get_facts()
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["fact_value"], "My favorite language is Python")
        self.assertEqual(facts[0]["fact_key"], "programming")

        # Format for prompt
        formatted = self.memory.format_facts_for_prompt()
        self.assertIn("RECALLED USER FACTS", formatted)
        self.assertIn("My favorite language is Python", formatted)

        # Delete fact
        deleted = self.memory.delete_fact(fact_id)
        self.assertTrue(deleted)
        self.assertEqual(len(self.memory.get_facts()), 0)

    def test_clear_all_facts(self):
        """Tests clearing all facts."""
        self.memory.add_fact("Fact 1")
        self.memory.add_fact("Fact 2")
        self.assertEqual(len(self.memory.get_facts()), 2)

        cleared = self.memory.clear_all_facts()
        self.assertEqual(cleared, 2)
        self.assertEqual(len(self.memory.get_facts()), 0)

    def test_session_message_recording(self):
        """Tests saving and retrieving chat turns."""
        self.memory.record_message("user", "Hello DUDE")
        self.memory.record_message("assistant", "Hi there!")

        messages = self.memory.get_session_messages()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello DUDE")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Hi there!")

        # Recent sessions
        sessions = self.memory.get_recent_sessions()
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["message_count"], 2)

    @patch("dude.core.brain.Groq")
    def test_brain_with_memory_integration(self, mock_groq_cls):
        """Tests that DudeBrain uses MemoryManager and injects facts into prompts."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "Got it! I will remember you like mangoes."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        brain = DudeBrain(config=self.config, memory=self.memory)

        # Initially no facts in system prompt
        self.assertNotIn("RECALLED USER FACTS", brain.get_history()[0]["content"])

        # Add a fact through brain
        brain.remember_fact("User loves mangoes", fact_key="preference")

        # System prompt should now contain the fact!
        system_content = brain.get_history()[0]["content"]
        self.assertIn("RECALLED USER FACTS", system_content)
        self.assertIn("User loves mangoes", system_content)

        # Generate response
        reply = brain.generate_response("Remember I love mangoes")
        self.assertEqual(reply, "Got it! I will remember you like mangoes.")

        # Verify messages were saved to SQLite
        db_messages = self.memory.get_session_messages()
        self.assertEqual(len(db_messages), 2)

        # Test starting fresh session: facts remain in system prompt, messages cleared
        brain.start_new_session("New Topic")
        self.assertEqual(brain.get_turn_count(), 0)
        self.assertIn("User loves mangoes", brain.get_history()[0]["content"])


if __name__ == "__main__":
    unittest.main()
