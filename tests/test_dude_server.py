"""
Unit tests for DUDE 0.4 Standalone Independent Server & API subsystem.
Covers REST API endpoints for status, telemetry, chat, memory CRUD, and notes.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from dude.config import Config
from dude.core.brain import DudeBrain
from dude.memory.database import MemoryDatabase
from dude.memory.manager import MemoryManager
from dude.server.app import create_app


class TestDudeServer(unittest.TestCase):
    """Test suite for DUDE independent FastAPI server."""

    def setUp(self):
        # Temp dir for SQLite database
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.test_dir.name) / "test_server_memory.db"
        self.mem_db = MemoryDatabase(db_path=self.db_path)
        self.mem_manager = MemoryManager(db=self.mem_db)

        self.config = Config(
            api_key="gsk_test_server_key",
            model="qwen/qwen3.8-27b",
            temperature=0.7,
            max_tokens=500,
            voice_enabled=False,
            server_host="127.0.0.1",
            server_port=8000,
        )

        # Mock Groq client inside DudeBrain
        self.brain = DudeBrain(
            config=self.config,
            memory=self.mem_manager,
        )

        self.app = create_app(brain=self.brain, config=self.config)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_status_endpoint(self):
        """Verifies GET /api/status returns version and configuration."""
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("version", data)
        self.assertIn("model", data)
        self.assertIn("facts_count", data)
        self.assertEqual(data["model"], "qwen/qwen3.8-27b")

    def test_telemetry_endpoint(self):
        """Verifies GET /api/telemetry returns hardware statistics."""
        res = self.client.get("/api/telemetry")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("cpu", data)
        self.assertIn("memory", data)
        self.assertIn("disk", data)

    def test_chat_endpoint_success(self):
        """Verifies POST /api/chat generates AI response."""
        with patch.object(self.brain, "generate_response", return_value="Hello! I am DUDE."):
            res = self.client.post("/api/chat", json={"message": "Hello", "speak": False})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["response"], "Hello! I am DUDE.")
            self.assertIn("session_id", data)

    def test_chat_endpoint_empty_message(self):
        """Verifies POST /api/chat rejects empty messages."""
        res = self.client.post("/api/chat", json={"message": "   "})
        self.assertEqual(res.status_code, 400)

    def test_memory_crud_endpoints(self):
        """Verifies full lifecycle of facts through /api/memory REST endpoints."""
        # 1. Initially empty
        res = self.client.get("/api/memory")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 0)

        # 2. Add fact
        res = self.client.post("/api/memory", json={
            "fact_value": "My favorite programming language is Python",
            "fact_key": "preference"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        fact_id = data["id"]
        self.assertGreater(fact_id, 0)

        # 3. List facts
        res = self.client.get("/api/memory")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["facts"][0]["fact_value"], "My favorite programming language is Python")

        # 4. Delete fact
        res = self.client.delete(f"/api/memory/{fact_id}")
        self.assertEqual(res.status_code, 200)

        # 5. Verify deleted
        res = self.client.get("/api/memory")
        self.assertEqual(res.json()["count"], 0)

    def test_notes_endpoints(self):
        """Verifies GET /api/notes and POST /api/notes."""
        res = self.client.post("/api/notes", json={
            "title": "ServerTestNote",
            "content": "Testing independent server notes endpoint"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

        # List notes
        res = self.client.get("/api/notes")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("notes", data)

    def test_voices_endpoint(self):
        """Verifies GET /api/voice/voices returns voice catalog."""
        res = self.client.get("/api/voice/voices")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("voices", data)
        self.assertIn("active", data)


if __name__ == "__main__":
    unittest.main()
