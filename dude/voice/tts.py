"""
Text-to-Speech (TTS) Engine for DUDE.
Supports high-definition neural voices via Edge-TTS and offline fallback via PyTTSx3.
"""

import os
import re
import asyncio
import tempfile
import threading
from typing import Dict, Optional

try:
    import edge_tts  # type: ignore
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _EDGE_TTS_AVAILABLE = False

try:
    import pygame  # type: ignore
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

try:
    import pyttsx3  # type: ignore
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False


class VoiceSynthesisError(Exception):
    """Raised when speech synthesis fails."""
    pass


RECOMMENDED_VOICES: Dict[str, str] = {
    "en-US-GuyNeural": "English (US) - Male (Friendly & Confident, Default)",
    "en-US-ChristopherNeural": "English (US) - Male (Calm & Professional)",
    "en-US-EricNeural": "English (US) - Male (Energetic & Dynamic)",
    "en-US-JennyNeural": "English (US) - Female (Warm & Natural)",
    "en-US-AriaNeural": "English (US) - Female (Expressive & Engaging)",
    "en-GB-RyanNeural": "English (UK) - Male (British Accent)",
    "en-GB-SoniaNeural": "English (UK) - Female (British Accent)",
    "en-IN-PrabhatNeural": "English (India) - Male (Indian Accent)",
    "en-IN-NeerjaNeural": "English (India) - Female (Indian Accent)",
}


def clean_text_for_speech(text: str) -> str:
    """
    Strips code blocks, markdown tags, tables, URLs, and excessive symbols
    so the speech sounds natural rather than reading syntax aloud.
    """
    if not text:
        return ""

    t = text

    # Remove code blocks ```...```
    t = re.sub(r'```[\s\S]*?```', ' [Code block omitted] ', t)

    # Remove inline code `...`
    t = re.sub(r'`([^`]+)`', r'\1', t)

    # Replace markdown links [anchor](url) with just the anchor text
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)

    # Remove raw URLs
    t = re.sub(r'https?://\S+', ' link ', t)

    # Remove markdown formatting characters (*, ~, #)
    t = re.sub(r'[*~#]+', '', t)

    # Remove markdown emphasis underscores (_italic_ or __bold__) without stripping snake_case variables
    t = re.sub(r'(?<!\w)__?|__?(?!\w)', '', t)

    # Remove markdown table rows (| ... |)
    t = re.sub(r'\|[^\n]+\|', '', t)

    # Remove horizontal rules
    t = re.sub(r'[-=_]{3,}', '', t)

    # Remove bullet markers (- or * at start of lines)
    t = re.sub(r'^\s*[-*+]\s+', '', t, flags=re.MULTILINE)

    # Condense multiple whitespaces/newlines into single spaces
    t = re.sub(r'\s+', ' ', t).strip()

    return t


class TTSEngine:
    """
    High-quality Text-To-Speech Engine using Microsoft Edge Neural Voices
    with seamless offline SAPI5 (pyttsx3) fallback.
    """

    def __init__(
        self,
        speaker: str = "en-US-GuyNeural",
        rate: str = "+0%",
        use_fallback_if_needed: bool = True
    ):
        self.speaker = speaker
        self.rate = rate
        self.use_fallback_if_needed = use_fallback_if_needed
        self._lock = threading.Lock()

    @staticmethod
    def get_recommended_voices() -> Dict[str, str]:
        """Returns the dictionary of popular recommended neural voices."""
        return dict(RECOMMENDED_VOICES)

    def _play_audio_file(self, file_path: str, wait: bool = True) -> None:
        """Plays an audio file (MP3) using Pygame mixer."""
        if not _PYGAME_AVAILABLE:
            raise VoiceSynthesisError("Pygame is not installed for audio playback.")

        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            if wait:
                clock = pygame.time.Clock()
                while pygame.mixer.music.get_busy():
                    clock.tick(20)

            # Release file handle before returning
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            pygame.mixer.quit()
        except Exception as e:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
            raise VoiceSynthesisError(f"Failed to play synthesized audio: {str(e)}") from e

    async def _synthesize_edge_async(self, text: str, output_path: str) -> None:
        """Asynchronously synthesizes speech using Edge-TTS."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.speaker,
            rate=self.rate
        )
        await communicate.save(output_path)

    def _speak_edge(self, text: str, wait: bool = True) -> bool:
        """Synthesizes and plays speech using Edge-TTS."""
        if not _EDGE_TTS_AVAILABLE or not _PYGAME_AVAILABLE:
            return False

        fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        try:
            # Run async edge_tts synthesis in synchronous caller
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new loop in separate thread if already in an active event loop
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.submit(
                            asyncio.run,
                            self._synthesize_edge_async(text, temp_path)
                        ).result()
                else:
                    loop.run_until_complete(self._synthesize_edge_async(text, temp_path))
            except RuntimeError:
                asyncio.run(self._synthesize_edge_async(text, temp_path))

            # Play the generated audio file
            self._play_audio_file(temp_path, wait=wait)
            return True

        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _speak_pyttsx3(self, text: str) -> bool:
        """Offline fallback using pyttsx3 (Windows SAPI5)."""
        if not _PYTTSX3_AVAILABLE:
            return False

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 180)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception:
            return False

    def speak(self, raw_text: str, wait: bool = True) -> bool:
        """
        Synthesizes and speaks text out loud.
        Strips markdown formatting, tries Edge-TTS neural voice first,
        and falls back to pyttsx3 if offline or if Edge-TTS fails.

        Returns True if speech was successfully output.
        """
        clean_text = clean_text_for_speech(raw_text)
        if not clean_text:
            return False

        with self._lock:
            # 1. Try high-definition Edge-TTS
            try:
                success = self._speak_edge(clean_text, wait=wait)
                if success:
                    return True
            except Exception:
                pass

            # 2. Fall back to offline pyttsx3 if enabled
            if self.use_fallback_if_needed:
                return self._speak_pyttsx3(clean_text)

            return False
