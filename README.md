# DUDE 0.4 - Independent Personal AI Assistant

**DUDE** is a 100% standalone, independent personal AI desktop and mobile application powered by **Groq** (`qwen/qwen3.8-27b`) with **Persistent SQLite Memory**, **Autonomous System Tools**, and a **Multimodal Voice Pipeline** (Edge-TTS Neural voices + Groq Whisper).

DUDE runs locally on your PC with zero third-party platform dependencies (no Telegram, no Discord, no cloud middleman).

---

## Key Capabilities

1. **Standalone Desktop Window (JARVIS Style)**:
   - Dedicated borderless desktop window on Windows with an ultra-modern obsidian & electric cyan Glassmorphism aesthetic.
   - Central **Glowing Reactive Voice Orb** that dynamically animates when Idle, Listening, Thinking, and Speaking.
2. **Local Async API Backend (`FastAPI`)**:
   - High-performance REST and WebSocket endpoints for chat, audio transcription, neural speech synthesis, hardware telemetry, memory vault, and desktop notes.
3. **Cross-Device Mobile PWA**:
   - Access DUDE from your phone on the same Wi-Fi (`http://<your-pc-ip>:8000`).
   - Installable directly to your phone's Home Screen with its own app icon and full-screen experience.
4. **Autonomous Desktop Tools**:
   - Real-time CPU, RAM, Disk, Battery telemetry via `psutil`.
   - Windows app launcher (Notepad, VS Code, Spotify, Calc, Paint, Explorer, Terminal).
   - Web browser search (Google, YouTube) and persistent local notes in `data/notes/`.
5. **Persistent Memory in SQLite**:
   - Automatically detects and remembers personal facts, preferences, and locations across sessions.
6. **Hands-Free Two-Way Voice Calls**:
   - Browser and terminal continuous voice call loops with neural speech and Groq Whisper transcription.

---

## Project Structure

```
Project DUDE/
│
├── dude/
│   ├── __init__.py          # Package initialization (__version__ = "0.4.0")
│   ├── config.py            # Environment configuration & Groq validation
│   ├── core/
│   │   ├── brain.py         # DudeBrain: coordinates memory, tools & Groq API
│   │   └── prompts.py       # Prompt builder with dynamic memory injection
│   ├── memory/
│   │   ├── database.py      # SQLite connection & schema management
│   │   └── manager.py       # MemoryManager: facts, profile & turn logging
│   ├── tools/
│   │   ├── registry.py      # ToolRegistry: schema generator & safe dispatcher
│   │   └── system.py        # System tools: stats, app launch, browser, notes, timers
│   ├── voice/
│   │   ├── stt.py           # STTEngine: microphone capture & Groq Whisper STT
│   │   ├── tts.py           # TTSEngine: Edge-TTS neural voices & PyTTSx3 fallback
│   │   └── service.py       # VoiceService: unified audio controller
│   ├── server/
│   │   ├── app.py           # FastAPI server with REST & WebSocket endpoints
│   │   └── static/          # Standalone client application assets
│   │       ├── index.html   # Modern responsive dashboard & voice orb
│   │       ├── manifest.json# PWA configuration for Desktop & Mobile install
│   │       ├── css/style.css# Glassmorphism & glowing animations
│   │       ├── js/app.js    # Client controller (chat, audio, telemetry, memory)
│   │       └── icons/       # SVG vector app icons
│   └── ui/
│       ├── desktop.py       # Standalone desktop window launcher
│       └── terminal.py      # Legacy Terminal CLI chat loop
│
├── data/                    # Local storage (ignored in git)
│   ├── dude_memory.db       # Persistent SQLite database
│   └── notes/               # Local user text notes
│
├── tests/
│   ├── test_dude_core.py    # Core brain & config tests (9 tests)
│   ├── test_dude_memory.py  # SQLite memory tests (5 tests)
│   ├── test_dude_voice.py   # Voice STT/TTS tests (10 tests)
│   ├── test_dude_tools.py   # System tools & function calling tests (11 tests)
│   └── test_dude_server.py  # Standalone server & API tests (7 tests)
│
├── main.py                  # Application entry point
├── requirements.txt         # Dependencies (fastapi, uvicorn, groq, psutil, edge-tts)
├── .env.example             # Template for API credentials & voice settings
└── README.md                # Full documentation
```

---

## Quick Start

### 1. Environment Configuration

Ensure your `.env` contains your Groq API key (free at [console.groq.com](https://console.groq.com/keys)):

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_TEMPERATURE=0.7
GROQ_MAX_TOKENS=500

# Voice Output & Input
DUDE_VOICE_ENABLED=true
DUDE_VOICE_SPEAKER=en-US-GuyNeural
DUDE_VOICE_RATE=+0%
GROQ_WHISPER_MODEL=whisper-large-v3-turbo

# Standalone Server Host & Port
DUDE_HOST=0.0.0.0
DUDE_PORT=8000
```

### 2. Launching DUDE

#### Standalone Desktop App Window (Default)
```powershell
.\.venv\Scripts\python.exe main.py
```
* Launches the local API backend and opens DUDE in a dedicated, borderless desktop window.
* Shows your local Wi-Fi IP address (e.g. `http://192.168.1.15:8000`) so you can open DUDE on your phone simultaneously!

#### Terminal CLI Mode
```powershell
.\.venv\Scripts\python.exe main.py --cli
```

#### Headless Server Mode (Background Hosting)
```powershell
.\.venv\Scripts\python.exe main.py --server-only
```

---

## REST & WebSocket API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | System status, active model, and memory count |
| `GET` | `/api/telemetry` | Real-time CPU, RAM, Disk, Battery & Uptime |
| `POST` | `/api/chat` | Send conversational prompt, executes tools autonomously |
| `GET` | `/api/memory` | List all persistent facts from SQLite |
| `POST` | `/api/memory` | Store a new fact into memory |
| `DELETE`| `/api/memory/{id}`| Delete a specific fact by ID |
| `GET` | `/api/notes` | List saved desktop notes |
| `POST` | `/api/notes` | Create a new desktop note |
| `POST` | `/api/voice/transcribe` | Transcribe browser mic audio via Groq Whisper |
| `POST` | `/api/voice/tts` | Synthesize neural MP3 speech via Edge-TTS |
| `WS` | `/api/ws/call` | Real-time continuous voice streaming |

---

## Running Verification Tests

Run the complete 42-test verification suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

---

## Roadmap

- [x] **Level 1**: Core AI Brain, session context, Groq integration, terminal UI.
- [x] **Level 2**: Persistent Memory (SQLite facts, session logs, `/remember`, `/forget`).
- [x] **Level 3**: System Tools & Automation (app launching, system stats, file tools, browser, timers).
- [x] **Level 4**: Voice Input/Output (Groq Whisper STT + Edge-TTS Neural Voice + `/call` mode).
- [x] **Level 5**: Standalone Independent App (FastAPI Local Backend + Standalone Desktop Window + Mobile PWA).
