"""
Unit tests for DUDE 0.3 Voice Input & Output subsystem.
Covers Config voice settings, text sanitization, STT Groq Whisper integration,
TTS engine logic, VoiceService controller, and UI voice commands.
"""

import io
import unittest
from unittest.mock import MagicMock, patch

from dude.config import Config
from dude.voice.stt import (
    STTEngine,
    VoiceRecordingError,
    VoiceTranscriptionError,
)
from dude.voice.tts import (
    TTSEngine,
    clean_text_for_speech,
    RECOMMENDED_VOICES,
)
from dude.voice.service import VoiceService
from dude.ui.terminal import DudeTerminalUI


class TestDudeVoice(unittest.TestCase):
    """Test suite for DUDE voice input and output features."""

    def setUp(self):
        self.config = Config(
            api_key="gsk_test_api_key_12345",
            model="qwen/qwen3.8-27b",
            temperature=0.7,
            max_tokens=800,
            voice_enabled=False,
            voice_speaker="en-US-GuyNeural",
            voice_rate="+0%",
            whisper_model="whisper-large-v3-turbo",
        )

    def test_voice_config_defaults(self):
        """Verifies that voice configuration defaults are set correctly."""
        self.assertFalse(self.config.voice_enabled)
        self.assertEqual(self.config.voice_speaker, "en-US-GuyNeural")
        self.assertEqual(self.config.voice_rate, "+0%")
        self.assertEqual(self.config.whisper_model, "whisper-large-v3-turbo")

    def test_text_cleaning_for_speech(self):
        """Verifies that markdown, code blocks, URLs, and table syntax are cleaned for speech."""
        raw_markdown = (
            "Here is the code:\n"
            "```python\nprint('hello')\n```\n"
            "Check [Google](https://google.com) and use `variable_name`.\n"
            "## Summary\n"
            "* Point 1\n"
            "* Point 2\n"
            "| col1 | col2 |\n"
            "**Bold text** and *italic*."
        )
        cleaned = clean_text_for_speech(raw_markdown)

        # Code block should be sanitized
        self.assertNotIn("print('hello')", cleaned)
        self.assertIn("[Code block omitted]", cleaned)

        # Markdown links replaced with link anchor text
        self.assertIn("Google", cleaned)
        self.assertNotIn("https://google.com", cleaned)

        # Inline code backticks stripped
        self.assertIn("variable_name", cleaned)
        self.assertNotIn("`", cleaned)

        # Markdown bold/headers symbols stripped
        self.assertNotIn("**", cleaned)
        self.assertNotIn("##", cleaned)
        self.assertIn("Bold text and italic.", cleaned)

    def test_stt_transcribe_success(self):
        """Verifies that STTEngine formats payload and returns Whisper transcription."""
        mock_groq = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello DUDE how are you"
        mock_groq.audio.transcriptions.create.return_value = mock_response

        stt = STTEngine(client=mock_groq, model="whisper-large-v3-turbo")
        result = stt.transcribe(b"fake_audio_bytes")

        self.assertEqual(result, "Hello DUDE how are you")
        mock_groq.audio.transcriptions.create.assert_called_once()
        call_kwargs = mock_groq.audio.transcriptions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "whisper-large-v3-turbo")
        self.assertEqual(call_kwargs["file"][0], "voice.wav")
        self.assertEqual(call_kwargs["file"][1], b"fake_audio_bytes")

    def test_stt_transcribe_empty_buffer(self):
        """Verifies that empty audio data raises VoiceTranscriptionError."""
        mock_groq = MagicMock()
        stt = STTEngine(client=mock_groq)
        with self.assertRaises(VoiceTranscriptionError):
            stt.transcribe(b"")

    @patch("dude.voice.stt.sd")
    def test_stt_record_audio_creates_wav(self, mock_sd):
        """Verifies that record_audio creates a valid WAV byte stream."""
        import numpy as np
        # Mock sounddevice return with 16000 int16 samples (1 second at 16kHz)
        fake_samples = np.zeros((16000, 1), dtype=np.int16)
        mock_sd.rec.return_value = fake_samples

        mock_groq = MagicMock()
        stt = STTEngine(client=mock_groq, sample_rate=16000)
        wav_bytes = stt.record_audio(duration=1.0)

        # Verify WAV header 'RIFF' and 'WAVE'
        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_bytes[:16])

    def test_tts_speak_fallback_pyttsx3(self):
        """Verifies that TTS engine falls back to pyttsx3 when Edge-TTS is unavailable."""
        tts = TTSEngine(speaker="en-US-GuyNeural")

        with patch.object(tts, "_speak_edge", return_value=False), \
             patch.object(tts, "_speak_pyttsx3", return_value=True) as mock_pyttsx3:
            success = tts.speak("Testing fallback speech", wait=True)
            self.assertTrue(success)
            mock_pyttsx3.assert_called_once_with("Testing fallback speech")

    def test_voice_service_toggle_and_config(self):
        """Verifies VoiceService toggles and speaker modifications."""
        mock_groq = MagicMock()
        service = VoiceService(config=self.config, groq_client=mock_groq)

        # Default is False
        self.assertFalse(service.enabled)

        # Toggle to True
        self.assertTrue(service.toggle())
        self.assertTrue(service.enabled)

        # Explicit set
        self.assertFalse(service.toggle(False))
        self.assertFalse(service.enabled)

        # Speaker management
        self.assertEqual(service.get_speaker(), "en-US-GuyNeural")
        service.set_speaker("en-US-ChristopherNeural")
        self.assertEqual(service.get_speaker(), "en-US-ChristopherNeural")

        # Available voices
        voices = service.get_available_voices()
        self.assertIn("en-US-GuyNeural", voices)
        self.assertIn("en-US-ChristopherNeural", voices)

    def test_voice_service_speak_if_enabled(self):
        """Verifies speak_if_enabled only speaks when enabled is True."""
        mock_groq = MagicMock()
        mock_tts = MagicMock()
        service = VoiceService(
            config=self.config,
            groq_client=mock_groq,
            tts_engine=mock_tts
        )

        # Disabled initially: should not speak
        service.enabled = False
        service.speak_if_enabled("Hello there")
        mock_tts.speak.assert_not_called()

        # Enabled: should speak
        service.enabled = True
        service.speak_if_enabled("Hello there")
        mock_tts.speak.assert_called_once_with("Hello there", wait=True)

    def test_terminal_ui_voice_commands(self):
        """Verifies terminal UI handles voice commands without exceptions."""
        mock_brain = MagicMock()
        mock_brain.config = self.config
        mock_brain.get_facts.return_value = []
        mock_voice = MagicMock()
        mock_voice.enabled = False
        mock_voice.get_speaker.return_value = "en-US-GuyNeural"
        mock_voice.get_available_voices.return_value = RECOMMENDED_VOICES
        mock_voice.is_microphone_available.return_value = True

        ui = DudeTerminalUI(brain=mock_brain, voice=mock_voice)

        # Test /voice on
        ui.handle_voice_toggle("on")
        mock_voice.toggle.assert_called_with(True)

        # Test /voice off
        ui.handle_voice_toggle("off")
        mock_voice.toggle.assert_called_with(False)

        # Test /voice speaker
        ui.handle_voice_toggle("speaker en-US-ChristopherNeural")
        mock_voice.set_speaker.assert_called_with("en-US-ChristopherNeural")

        # Test /speak
        ui.handle_speak("Hello World")
        mock_voice.speak.assert_called_with("Hello World")

        # Test /voices
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.display_voices()
            output = mock_out.getvalue()
            self.assertIn("en-US-GuyNeural", output)

    def test_terminal_ui_call_command(self):
        """Verifies hands-free call mode terminates cleanly when user says goodbye."""
        mock_brain = MagicMock()
        mock_brain.config = self.config
        mock_brain.get_facts.return_value = []
        mock_voice = MagicMock()
        mock_voice.is_microphone_available.return_value = True
        # Simulate user saying "goodbye" on the first turn
        mock_voice.listen.return_value = "goodbye"

        ui = DudeTerminalUI(brain=mock_brain, voice=mock_voice)
        ui.handle_call()

        mock_voice.speak.assert_called_with("Ending hands-free call. Talk to you soon!")


if __name__ == "__main__":
    unittest.main()

