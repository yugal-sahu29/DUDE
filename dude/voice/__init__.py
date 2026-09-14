"""
Voice Subsystem for DUDE 0.3.
Provides Speech-to-Text (STT) via Groq Whisper and Natural Text-to-Speech (TTS) via Edge-TTS & PyTTSx3.
"""

from dude.voice.stt import (
    STTEngine,
    VoiceError,
    VoiceRecordingError,
    VoiceTranscriptionError,
)
from dude.voice.tts import (
    TTSEngine,
    VoiceSynthesisError,
)
from dude.voice.service import VoiceService

__all__ = [
    "VoiceError",
    "VoiceRecordingError",
    "VoiceTranscriptionError",
    "VoiceSynthesisError",
    "STTEngine",
    "TTSEngine",
    "VoiceService",
]
