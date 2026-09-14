"""
Configuration loader for DUDE.
Loads and validates environment variables from .env file for Groq.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    def load_dotenv(dotenv_path: Optional[Path] = None, override: bool = True) -> bool:
        """Fallback built-in .env parser if python-dotenv is not installed."""
        target = Path(dotenv_path) if dotenv_path else Path(".env")
        if not target.is_file():
            return False
        try:
            with open(target, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if override or key not in os.environ:
                            os.environ[key] = val
            return True
        except Exception:
            return False


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


@dataclass
class Config:
    """Application configuration container."""
    api_key: str
    model: str = "qwen/qwen3.8-27b"
    temperature: float = 0.7
    max_tokens: int = 500
    voice_enabled: bool = True
    voice_speaker: str = "en-US-GuyNeural"
    voice_rate: str = "+0%"
    whisper_model: str = "whisper-large-v3-turbo"
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    @classmethod
    def load(cls) -> "Config":
        """
        Loads configuration from environment variables and .env file.
        Raises ConfigurationError if GROQ_API_KEY is not configured.
        """
        project_root = Path(__file__).resolve().parent.parent
        env_path = project_root / ".env"
        
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            load_dotenv(override=True)

        api_key = os.getenv("GROQ_API_KEY", "").strip()

        if not api_key or api_key == "your_groq_api_key_here":
            raise ConfigurationError(
                "GROQ_API_KEY is missing or invalid in your .env file.\n"
                "Please follow these steps:\n"
                "  1. Open your '.env' file in Project DUDE\n"
                "  2. Add: GROQ_API_KEY=gsk_...\n"
                "  3. Save the file and restart DUDE."
            )

        model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip() or "qwen/qwen3.8-27b"

        # Parse temperature
        raw_temp = os.getenv("GROQ_TEMPERATURE", "0.7").strip()
        try:
            temperature = float(raw_temp)
            if not (0.0 <= temperature <= 2.0):
                temperature = 0.7
        except ValueError:
            temperature = 0.7

        # Parse max_tokens (default 500 to stay within Groq free-tier 1000 OTPM limit)
        raw_tokens = os.getenv("GROQ_MAX_TOKENS", "500").strip()
        try:
            max_tokens = int(raw_tokens)
            if max_tokens <= 0:
                max_tokens = 500
        except ValueError:
            max_tokens = 500

        # Voice configuration (default to True for automatic voice response)
        raw_voice_enabled = os.getenv("DUDE_VOICE_ENABLED", os.getenv("VOICE_ENABLED", "true")).strip().lower()
        voice_enabled = raw_voice_enabled in ("true", "1", "yes", "on")


        voice_speaker = (
            os.getenv("DUDE_VOICE_SPEAKER") or os.getenv("VOICE_SPEAKER") or "en-US-GuyNeural"
        ).strip()

        voice_rate = (
            os.getenv("DUDE_VOICE_RATE") or os.getenv("VOICE_RATE") or "+0%"
        ).strip()

        whisper_model = (
            os.getenv("GROQ_WHISPER_MODEL") or os.getenv("WHISPER_MODEL") or "whisper-large-v3-turbo"
        ).strip()

        # Server host & port configuration
        server_host = os.getenv("DUDE_HOST", "0.0.0.0").strip() or "0.0.0.0"
        raw_port = os.getenv("DUDE_PORT", "8000").strip()
        try:
            server_port = int(raw_port)
            if not (1 <= server_port <= 65535):
                server_port = 8000
        except ValueError:
            server_port = 8000

        return cls(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            voice_enabled=voice_enabled,
            voice_speaker=voice_speaker,
            voice_rate=voice_rate,
            whisper_model=whisper_model,
            server_host=server_host,
            server_port=server_port,
        )

