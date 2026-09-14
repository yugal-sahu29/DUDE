"""
High-Level Voice Service for DUDE.
Coordinates Speech-To-Text (Groq Whisper) and Text-To-Speech (Edge-TTS / PyTTSx3).
"""

import threading
from typing import Dict, Optional
from groq import Groq  # type: ignore

from dude.config import Config
from dude.voice.stt import STTEngine, VoiceRecordingError, VoiceTranscriptionError
from dude.voice.tts import TTSEngine, clean_text_for_speech


class VoiceService:
    """
    Central controller for DUDE's voice input and output subsystems.
    """

    def __init__(
        self,
        config: Config,
        groq_client: Optional[Groq] = None,
        stt_engine: Optional[STTEngine] = None,
        tts_engine: Optional[TTSEngine] = None,
    ):
        self.config = config
        self.enabled: bool = config.voice_enabled
        self.groq_client = groq_client or Groq(api_key=config.api_key)

        self.stt = stt_engine or STTEngine(
            client=self.groq_client,
            model=config.whisper_model,
        )

        self.tts = tts_engine or TTSEngine(
            speaker=config.voice_speaker,
            rate=config.voice_rate,
        )

    def is_microphone_available(self) -> bool:
        """Checks if a microphone input device is connected and accessible."""
        return self.stt.is_microphone_available()

    def toggle(self, state: Optional[bool] = None) -> bool:
        """
        Toggles voice output state, or sets to an explicit boolean if provided.
        Returns the new state.
        """
        if state is not None:
            self.enabled = state
        else:
            self.enabled = not self.enabled
        return self.enabled

    def set_speaker(self, speaker_id: str) -> None:
        """Changes the active TTS voice."""
        self.tts.speaker = speaker_id.strip()

    def get_speaker(self) -> str:
        """Returns the currently active voice speaker ID."""
        return self.tts.speaker

    def get_available_voices(self) -> Dict[str, str]:
        """Returns the dictionary of recommended voices."""
        return self.tts.get_recommended_voices()

    def speak(self, text: str, wait: bool = True) -> bool:
        """
        Unconditionally speaks the given text out loud.
        """
        return self.tts.speak(text, wait=wait)

    def speak_if_enabled(self, text: str, async_mode: bool = False) -> bool:
        """
        Speaks text only if voice output is enabled.
        Can run asynchronously in a daemon thread so the terminal output isn't blocked.
        """
        if not self.enabled:
            return False

        if async_mode:
            thread = threading.Thread(
                target=self.tts.speak,
                args=(text,),
                kwargs={"wait": True},
                daemon=True
            )
            thread.start()
            return True
        else:
            return self.tts.speak(text, wait=True)

    def listen(self, duration: float = 5.0) -> str:
        """
        Records user audio from the microphone for the specified duration
        and returns the transcribed text.

        Raises:
            VoiceRecordingError: If microphone is unavailable.
            VoiceTranscriptionError: If Whisper transcription fails.
        """
        return self.stt.listen_and_transcribe(duration=duration)
