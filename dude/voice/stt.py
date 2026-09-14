"""
Speech-to-Text (STT) Engine for DUDE.
Captures audio from microphone and transcribes it via Groq Whisper API.
"""

import io
import wave
from typing import Optional
from groq import Groq  # type: ignore
import groq  # type: ignore

try:
    import sounddevice as sd  # type: ignore
    import numpy as np  # type: ignore
    _AUDIO_DEVICES_AVAILABLE = True
except Exception:
    _AUDIO_DEVICES_AVAILABLE = False


class VoiceError(Exception):
    """Base exception for voice subsystem errors."""
    pass


class VoiceRecordingError(VoiceError):
    """Raised when audio recording fails or microphone is unavailable."""
    pass


class VoiceTranscriptionError(VoiceError):
    """Raised when speech transcription fails."""
    pass


class STTEngine:
    """
    Handles microphone audio capture and Whisper transcription via Groq.
    """

    def __init__(
        self,
        client: Groq,
        model: str = "whisper-large-v3-turbo",
        sample_rate: int = 16000,
    ):
        self.client = client
        self.model = model
        self.sample_rate = sample_rate

    @staticmethod
    def is_microphone_available() -> bool:
        """Checks whether an active audio input device is detected."""
        if not _AUDIO_DEVICES_AVAILABLE:
            return False
        try:
            devices = sd.query_devices()
            # Look for at least one device with max_input_channels > 0
            for d in devices:
                if d.get("max_input_channels", 0) > 0:
                    return True
            return False
        except Exception:
            return False

    def record_audio(
        self,
        duration: float = 5.0,
        sample_rate: Optional[int] = None
    ) -> bytes:
        """
        Records microphone audio for the specified duration (in seconds)
        and returns the data encoded as a standard 16-bit mono WAV in bytes.

        Raises:
            VoiceRecordingError: If microphone is unavailable or recording errors occur.
        """
        if not _AUDIO_DEVICES_AVAILABLE:
            raise VoiceRecordingError(
                "Audio capture library (sounddevice) is not available or failed to initialize."
            )

        sr = sample_rate or self.sample_rate
        total_frames = int(duration * sr)

        try:
            # Record int16 mono audio
            recording = sd.rec(
                frames=total_frames,
                samplerate=sr,
                channels=1,
                dtype="int16",
            )
            sd.wait()
        except Exception as e:
            raise VoiceRecordingError(
                f"Failed to record audio from microphone: {str(e)}"
            ) from e

        # Pack into WAV byte buffer
        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(sr)
                wf.writeframes(recording.tobytes())
            return buffer.getvalue()
        except Exception as e:
            raise VoiceRecordingError(f"Failed to encode WAV audio: {str(e)}") from e

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "voice.wav"
    ) -> str:
        """
        Sends audio WAV bytes to Groq Whisper for transcription.

        Raises:
            VoiceTranscriptionError: If the transcription API request fails.
        """
        if not audio_bytes:
            raise VoiceTranscriptionError("Audio buffer is empty.")

        try:
            file_payload = (filename, audio_bytes, "audio/wav")
            response = self.client.audio.transcriptions.create(
                file=file_payload,
                model=self.model,
                response_format="json",
            )
            transcription = getattr(response, "text", "") or ""
            return transcription.strip()

        except groq.AuthenticationError as e:
            raise VoiceTranscriptionError(
                "Groq authentication failed during speech transcription. Please check GROQ_API_KEY."
            ) from e
        except groq.APIError as e:
            raise VoiceTranscriptionError(
                f"Groq Whisper transcription API error: {e.message}"
            ) from e
        except Exception as e:
            raise VoiceTranscriptionError(
                f"Unexpected error during transcription: {str(e)}"
            ) from e

    def listen_and_transcribe(self, duration: float = 5.0) -> str:
        """
        Convenience method: records audio from microphone and returns transcribed text.
        """
        audio_bytes = self.record_audio(duration=duration)
        return self.transcribe(audio_bytes)
