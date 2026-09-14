"""
FastAPI Application Factory for Project DUDE.
Provides REST APIs, WebSocket channels, and static file serving
for the independent desktop and mobile application.
"""

import os
import io
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dude import __version__
from dude.config import Config
from dude.core.brain import (
    DudeBrain,
    DudeAuthenticationError,
    DudeRateLimitError,
    DudeConnectionError,
    DudeAPIError,
    DudeBrainError,
)
from dude.tools.system import get_system_stats, create_note, list_notes, NOTES_DIR, get_local_ip
from dude.voice.service import VoiceService
from dude.voice.tts import RECOMMENDED_VOICES, clean_text_for_speech

try:
    import edge_tts  # type: ignore
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _EDGE_TTS_AVAILABLE = False


# --------------------------------------------------------------------------
# Request / Response Schemas
# --------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    speak: bool = False


class MemoryCreateRequest(BaseModel):
    fact_value: str
    fact_key: Optional[str] = None


class NoteCreateRequest(BaseModel):
    title: str
    content: str


class TTSRequest(BaseModel):
    text: str
    speaker: Optional[str] = None


# --------------------------------------------------------------------------
# App Factory
# --------------------------------------------------------------------------

def create_app(
    brain: Optional[DudeBrain] = None,
    voice: Optional[VoiceService] = None,
    config: Optional[Config] = None,
) -> FastAPI:
    """Creates and configures the FastAPI independent app instance."""
    app_config = config or Config.load()
    app_brain = brain or DudeBrain(config=app_config)
    app_voice = voice or VoiceService(config=app_config)

    app = FastAPI(
        title="Project DUDE",
        description="Independent Personal AI Assistant Server",
        version=__version__,
    )

    # Enable Cross-Origin Resource Sharing for local network devices (e.g. mobile on Wi-Fi)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static assets directory
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------------
    # System & Status Endpoints
    # ----------------------------------------------------------------------

    @app.get("/api/status")
    async def get_status() -> Dict[str, Any]:
        """Returns DUDE system status, active model, and memory count."""
        facts = app_brain.get_facts()
        local_ip = get_local_ip()
        return {
            "version": __version__,
            "model": app_brain.config.model,
            "facts_count": len(facts),
            "voice_enabled": app_voice.enabled,
            "active_speaker": app_voice.get_speaker(),
            "microphone_available": app_voice.is_microphone_available(),
            "server_host": app_brain.config.server_host,
            "server_port": app_brain.config.server_port,
            "local_ip": local_ip,
            "mobile_url": f"http://{local_ip}:{app_brain.config.server_port}",
        }

    @app.get("/api/telemetry")
    async def get_telemetry() -> Dict[str, Any]:
        """Returns real-time hardware telemetry: CPU, RAM, Disk, Battery, Uptime."""
        return get_system_stats()

    # ----------------------------------------------------------------------
    # Chat & Autonomous Execution Endpoint
    # ----------------------------------------------------------------------

    @app.post("/api/chat")
    async def chat(req: ChatRequest) -> Dict[str, Any]:
        """
        Processes conversational messages, executes requested desktop tools
        autonomously, and returns the assistant response.
        """
        user_msg = req.message.strip()
        if not user_msg:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        executed_tools: List[Dict[str, Any]] = []

        def _tool_recorder(tool_name: str, args: Dict[str, Any]):
            executed_tools.append({"tool": tool_name, "args": args})

        # Save previous callback and attach request-scoped recorder
        prev_callback = app_brain.on_tool_call
        app_brain.on_tool_call = _tool_recorder

        initial_facts = len(app_brain.get_facts())

        try:
            response_text = app_brain.generate_response(user_msg)
        except DudeAuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except DudeRateLimitError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except DudeConnectionError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except (DudeAPIError, DudeBrainError, ValueError) as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            app_brain.on_tool_call = prev_callback

        current_facts = app_brain.get_facts()
        new_facts = current_facts[initial_facts:] if len(current_facts) > initial_facts else []

        # If user explicitly requested audio spoken on host PC speakers
        if req.speak and app_voice.enabled:
            app_voice.speak_if_enabled(response_text, async_mode=True)

        return {
            "response": response_text,
            "tools_executed": executed_tools,
            "new_facts": new_facts,
            "session_id": app_brain.memory.current_session_id,
        }

    # ----------------------------------------------------------------------
    # Memory CRUD Endpoints
    # ----------------------------------------------------------------------

    @app.get("/api/memory")
    async def list_memory() -> Dict[str, Any]:
        """Returns all persistent facts stored in SQLite."""
        facts = app_brain.get_facts()
        return {"count": len(facts), "facts": facts}

    @app.post("/api/memory")
    async def add_memory(req: MemoryCreateRequest) -> Dict[str, Any]:
        """Stores a new fact into persistent memory."""
        val = req.fact_value.strip()
        if not val:
            raise HTTPException(status_code=400, detail="Fact value cannot be empty.")
        fact_id = app_brain.remember_fact(val, req.fact_key)
        return {"status": "success", "id": fact_id, "fact_value": val, "fact_key": req.fact_key}

    @app.delete("/api/memory/{fact_id}")
    async def delete_memory(fact_id: int) -> Dict[str, Any]:
        """Deletes a specific fact by ID."""
        deleted = app_brain.forget_fact(fact_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found.")
        return {"status": "success", "deleted_id": fact_id}

    @app.delete("/api/memory")
    async def clear_all_memory() -> Dict[str, Any]:
        """Clears all persistent facts."""
        count = app_brain.clear_all_facts()
        return {"status": "success", "cleared_count": count}

    # ----------------------------------------------------------------------
    # Notes Endpoints
    # ----------------------------------------------------------------------

    @app.get("/api/notes")
    async def get_notes() -> Dict[str, Any]:
        """Lists all desktop notes."""
        return list_notes()

    @app.post("/api/notes")
    async def add_note(req: NoteCreateRequest) -> Dict[str, Any]:
        """Creates a new desktop note."""
        if not req.title.strip() or not req.content.strip():
            raise HTTPException(status_code=400, detail="Title and content are required.")
        return create_note(req.title, req.content)

    @app.get("/api/notes/{name}")
    async def get_note_content(name: str) -> Dict[str, Any]:
        """Reads content of a specific note file."""
        clean_name = os.path.basename(name)
        if not clean_name.endswith(".txt"):
            clean_name += ".txt"
        note_file = NOTES_DIR / clean_name
        if not note_file.exists():
            raise HTTPException(status_code=404, detail="Note not found.")
        try:
            with open(note_file, "r", encoding="utf-8") as f:
                content = f.read()
            return {"name": note_file.stem, "content": content}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ----------------------------------------------------------------------
    # Voice STT & TTS Endpoints
    # ----------------------------------------------------------------------

    @app.get("/api/voice/voices")
    async def get_voices() -> Dict[str, Any]:
        """Returns recommended neural voices and the active speaker."""
        return {
            "active": app_voice.get_speaker(),
            "voices": RECOMMENDED_VOICES,
        }

    @app.post("/api/voice/transcribe")
    async def transcribe_audio(audio: UploadFile = File(...)) -> Dict[str, Any]:
        """
        Accepts audio from the client browser microphone and transcribes it
        using Groq's whisper-large-v3-turbo model.
        """
        suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            content = await audio.read()
            tmp.write(content)

        try:
            with open(tmp_path, "rb") as f:
                transcription = app_voice.groq_client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), f.read()),
                    model=app_config.whisper_model,
                    language="en",
                    response_format="json",
                )
            transcribed_text = getattr(transcription, "text", "") or ""
            return {"text": transcribed_text.strip()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    @app.post("/api/voice/tts")
    async def text_to_speech(req: TTSRequest):
        """
        Generates high-definition neural speech via Edge-TTS and returns an MP3 stream
        for smooth playback on client devices (Desktop or Mobile).
        """
        clean_text = clean_text_for_speech(req.text)
        if not clean_text:
            raise HTTPException(status_code=400, detail="Text for speech cannot be empty.")

        speaker = req.speaker or app_voice.get_speaker()

        if not _EDGE_TTS_AVAILABLE:
            raise HTTPException(status_code=501, detail="Edge-TTS engine is not available on server.")

        fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=speaker,
                rate=app_voice.tts.rate,
            )
            await communicate.save(temp_path)

            with open(temp_path, "rb") as f:
                mp3_bytes = f.read()

            return Response(content=mp3_bytes, media_type="audio/mpeg")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    # ----------------------------------------------------------------------
    # WebSocket Channel for Real-Time Call Mode
    # ----------------------------------------------------------------------

    @app.websocket("/api/ws/call")
    async def websocket_call(websocket: WebSocket):
        """
        Bidirectional WebSocket channel for continuous hands-free voice/chat streaming.
        """
        await websocket.accept()
        try:
            while True:
                data_text = await websocket.receive_text()
                try:
                    payload = json.loads(data_text)
                except Exception:
                    payload = {"message": data_text}

                user_msg = payload.get("message", "").strip()
                if not user_msg:
                    continue

                # Notify client: thinking
                await websocket.send_json({"type": "status", "status": "thinking"})

                try:
                    response_text = app_brain.generate_response(user_msg)
                    await websocket.send_json({
                        "type": "response",
                        "response": response_text,
                        "session_id": app_brain.memory.current_session_id,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

        except WebSocketDisconnect:
            pass

    # ----------------------------------------------------------------------
    # Static Assets & PWA UI Serving
    # ----------------------------------------------------------------------

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
