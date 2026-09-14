"""
Verification tests for DUDE 0.1 Core Brain and Configuration (Groq Engine).
"""

import unittest
from unittest.mock import MagicMock, patch
import groq

from dude.config import Config, ConfigurationError
from dude.core.brain import (
    DudeBrain,
    DudeBrainError,
    DudeAuthenticationError,
    DudeRateLimitError,
    DudeConnectionError,
    DudeAPIError,
)


class TestDudeCore(unittest.TestCase):
    def setUp(self):
        self.config = Config(api_key="gsk_test_dummy_key", model="llama-3.3-70b-versatile", temperature=0.7)

    @patch("dude.core.brain.Groq")
    def test_brain_initialization(self, mock_groq_cls):
        brain = DudeBrain(config=self.config)
        history = brain.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["role"], "system")
        self.assertIn("DUDE", history[0]["content"])

    @patch("dude.config.load_dotenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_config_missing_key_raises_error(self, mock_load_dotenv):
        with self.assertRaises(ConfigurationError) as ctx:
            Config.load()
        self.assertIn("GROQ_API_KEY is missing", str(ctx.exception))

    @patch("dude.config.load_dotenv")
    @patch.dict("os.environ", {"GROQ_API_KEY": "gsk_validtestkey123", "GROQ_MODEL": "llama-3.1-8b-instant", "GROQ_TEMPERATURE": "0.5"}, clear=True)
    def test_config_valid_loading(self, mock_load_dotenv):
        config = Config.load()
        self.assertEqual(config.api_key, "gsk_validtestkey123")
        self.assertEqual(config.model, "llama-3.1-8b-instant")
        self.assertEqual(config.temperature, 0.5)

    @patch("dude.core.brain.Groq")
    def test_brain_conversation_history_persistence(self, mock_groq_cls):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Mock Groq chat completions response
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello! I am DUDE. How can I help you today?"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        brain = DudeBrain(config=self.config)
        reply1 = brain.generate_response("Hi DUDE")

        self.assertEqual(reply1, "Hello! I am DUDE. How can I help you today?")
        self.assertEqual(len(brain.get_history()), 3)  # system + user + assistant
        self.assertEqual(brain.get_turn_count(), 2)

        # Turn 2
        mock_choice.message.content = "Your name is Alice!"
        reply2 = brain.generate_response("What is my name?")

        self.assertEqual(reply2, "Your name is Alice!")
        history = brain.get_history()
        self.assertEqual(len(history), 5)  # system + user + assistant + user + assistant
        self.assertEqual(brain.get_turn_count(), 4)

        # Verify all messages were passed to client on second turn
        call_args = mock_client.chat.completions.create.call_args[1]
        messages_sent = call_args["messages"]
        self.assertEqual(len(messages_sent), 4)  # system + user1 + assistant1 + user2

    @patch("dude.core.brain.Groq")
    def test_brain_clear_history(self, mock_groq_cls):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Sure thing!"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        brain = DudeBrain(config=self.config)
        brain.generate_response("Tell me something")
        self.assertEqual(len(brain.get_history()), 3)

        brain.clear_history()
        self.assertEqual(len(brain.get_history()), 1)
        self.assertEqual(brain.get_history()[0]["role"], "system")
        self.assertEqual(brain.get_turn_count(), 0)

    @patch("dude.core.brain.Groq")
    def test_empty_input_validation(self, mock_groq_cls):
        brain = DudeBrain(config=self.config)
        with self.assertRaises(ValueError):
            brain.generate_response("   ")

    @patch("dude.core.brain.Groq")
    def test_authentication_error_handling(self, mock_groq_cls):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = groq.AuthenticationError(
            message="Invalid API Key", response=MagicMock(), body=None
        )

        brain = DudeBrain(config=self.config)
        with self.assertRaises(DudeAuthenticationError):
            brain.generate_response("Hello")

        # Ensure history is rolled back to just system message
        self.assertEqual(len(brain.get_history()), 1)

    @patch("dude.core.brain.Groq")
    def test_rate_limit_error_handling(self, mock_groq_cls):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = groq.RateLimitError(
            message="Rate limit exceeded", response=MagicMock(), body=None
        )

        brain = DudeBrain(config=self.config)
        with self.assertRaises(DudeRateLimitError):
            brain.generate_response("Hello")

        self.assertEqual(len(brain.get_history()), 1)

    @patch("dude.core.brain.Groq")
    def test_connection_error_handling(self, mock_groq_cls):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = groq.APIConnectionError(
            request=MagicMock()
        )

        brain = DudeBrain(config=self.config)
        with self.assertRaises(DudeConnectionError):
            brain.generate_response("Hello")

        self.assertEqual(len(brain.get_history()), 1)


if __name__ == "__main__":
    unittest.main()
