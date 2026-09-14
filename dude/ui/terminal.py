"""
Terminal Chat Interface for DUDE 0.4.
Provides an interactive command-line interface with persistent memory,
autonomous system tools execution, and multimodal voice capabilities.
"""

import sys
from typing import Optional, Dict, Any

from dude.core.brain import (
    DudeBrain,
    DudeBrainError,
    DudeAuthenticationError,
    DudeRateLimitError,
    DudeConnectionError,
    DudeAPIError,
)
from dude.voice.service import VoiceService
from dude.voice.stt import VoiceRecordingError, VoiceTranscriptionError
from dude.tools.system import get_system_stats, launch_app, open_browser, list_notes

BANNER = r"""
===========================================================
  ____  _   _ ____  _____     ___   _  _   
 |  _ \| | | |  _ \| ____|   / _ \ | || |  
 | | | | | | | | | |  _|    | | | || || |_ 
 | |_| | |_| | |_| | |___   | |_| ||__   _|
 |____/ \___/|____/|_____|   \___(_)  |_|  
                                           
  DUDE 0.4 - Personal AI Assistant (Tools & Voice)
===========================================================
 Autonomous Tools: Ask DUDE to launch apps, check stats, open sites, or take notes!
 Press [Enter] on empty line to speak, or type /call for hands-free mode!
 Tool Commands  : /stats, /open <app|url>, /notes
 Voice Commands : /call, /talk [sec], /voice [on|off], /speak <text>, /voices
 Memory Commands: /remember <fact>, /memory, /forget <id|all>
 Chat Commands  : /new, /clear, /sessions, /history, /help, /exit
===========================================================
"""


class DudeTerminalUI:
    """
    Manages interactive terminal sessions for DUDE with persistent memory,
    autonomous tool execution, and voice interaction.
    """

    def __init__(self, brain: DudeBrain, voice: Optional[VoiceService] = None):
        self.brain = brain
        self.voice = voice or VoiceService(brain.config)

        # Connect brain tool execution notification callback
        self.brain.on_tool_call = self._on_tool_call_notification

    def _on_tool_call_notification(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Displays subtle feedback when DUDE invokes a system automation tool."""
        sys.stdout.write("\033[K")
        target_info = f" ({args})" if args else ""
        print(f"[TOOL] Executing '{tool_name}'{target_info}...", flush=True)

    def display_banner(self) -> None:
        """Displays the startup banner, session info, tools count, and voice status."""
        print(BANNER)
        facts = self.brain.get_facts()
        voice_state = "ON (Auto-Speak)" if self.voice.enabled else "OFF"
        mic_state = "Connected" if self.voice.is_microphone_available() else "Not Detected"
        tool_count = len(getattr(self.brain.tools, "_tools", {}))

        print(f"[*] Model          : {self.brain.config.model}")
        print(f"[*] Memory         : {len(facts)} fact(s) active in SQLite")
        print(f"[*] System Tools   : {tool_count} automation tools available")
        print(f"[*] Voice Output   : {voice_state} (Speaker: {self.voice.get_speaker()})")
        print(f"[*] Microphone     : {mic_state}")
        print(f"[*] Ready! Talk to DUDE below (Type or press Enter to speak):\n")

    def display_help(self) -> None:
        """Displays available interactive commands."""
        print("\n--- Available Commands ---")
        print("  System & Tool Commands:")
        print("    /stats            : Display real-time CPU, RAM, Disk, Battery & Uptime")
        print("    /open <app|url>   : Quick-launch application or URL (e.g. /open notepad, /open youtube.com)")
        print("    /notes            : View all notes saved in data/notes/")
        print("\n  Voice Commands:")
        print("    /call             : Hands-free continuous voice call (speak and listen back-and-forth)")
        print("    [Enter]           : Press Enter on an empty line to speak immediately (no typing needed)")
        print("    /talk [sec]       : Speak into microphone (default 5s) and get an AI response")
        print("    /voice [on|off]   : Toggle automatic voice output for AI replies")
        print("    /voice speaker <id>: Switch active neural voice (e.g. /voice speaker en-US-ChristopherNeural)")
        print("    /voices           : List available neural voice models")
        print("    /speak <text>     : Speak custom text aloud")
        print("\n  Memory Commands:")
        print("    /remember <text>  : Save a fact to persistent memory (e.g. /remember I like Mango)")
        print("    /memory           : View all stored persistent facts")
        print("    /forget <id|all>  : Delete a specific fact by ID or erase all facts")
        print("\n  Chat Commands:")
        print("    /new              : Start a fresh chat session (keeps persistent facts)")
        print("    /sessions         : List recent conversation sessions")
        print("    /history          : View turns in current session")
        print("    /clear            : Clear active session messages")
        print("    /help             : Show this help guide")
        print("    /exit or /quit    : Exit DUDE (or press Ctrl+C)")
        print("--------------------------\n")

    def display_system_stats(self) -> None:
        """Displays formatted real-time hardware telemetry."""
        stats = get_system_stats()
        if stats.get("status") == "error":
            print(f"\n[!] Error reading system stats: {stats.get('message')}\n")
            return

        print("\n--- Real-Time System Telemetry ---")
        print(f"  OS Platform : {stats.get('os')}")
        print(f"  System Uptime: {stats.get('uptime')}")
        cpu = stats.get("cpu", {})
        print(f"  CPU Load    : {cpu.get('usage_percent')} ({cpu.get('cores')} logical cores)")
        mem = stats.get("memory", {})
        print(f"  RAM Memory  : {mem.get('used_gb')} GB used / {mem.get('total_gb')} GB total ({mem.get('usage_percent')})")
        disk = stats.get("disk", {})
        print(f"  Disk Space  : {disk.get('free_gb')} GB free / {disk.get('total_gb')} GB total ({disk.get('usage_percent')} used)")
        bat = stats.get("battery", {})
        if "percent" in bat:
            print(f"  Battery     : {bat.get('percent')}% ({bat.get('charging_status')})")
        else:
            print(f"  Battery     : {bat.get('status', 'N/A')}")
        print("----------------------------------\n")

    def display_notes(self) -> None:
        """Displays saved local notes."""
        result = list_notes()
        notes = result.get("notes", [])
        if not notes:
            print("\n[!] No notes found in data/notes/. Ask DUDE to save a note anytime!\n")
            return

        print(f"\n--- Saved Notes ({len(notes)} items) ---")
        for n in notes:
            print(f"  * {n['name']} ({n['modified']})")
            print(f"    Preview: {n['preview']}")
        print("----------------------------------------\n")

    def handle_open(self, target: str) -> None:
        """Quickly opens an application or browser URL."""
        clean_target = target.strip()
        if not clean_target:
            print("\n[!] Usage: /open <app_name | url>")
            print("    Example: /open notepad OR /open github.com\n")
            return

        if clean_target.startswith(("http://", "https://")) or any(clean_target.endswith(ext) for ext in (".com", ".org", ".net", ".io", ".dev", ".edu")):
            res = open_browser(url=clean_target)
            print(f"\n[+] {res.get('message')}\n")
        else:
            res = launch_app(clean_target)
            if res.get("status") == "success":
                print(f"\n[+] {res.get('message')}\n")
            else:
                print(f"\n[!] {res.get('message')}\n")

    def display_memory(self) -> None:
        """Displays all facts stored in persistent memory."""
        facts = self.brain.get_facts()
        if not facts:
            print("\n[!] Persistent memory is currently empty. Use '/remember <fact>' to add one.\n")
            return

        print(f"\n--- Stored Facts & Profile ({len(facts)} items) ---")
        for f in facts:
            fact_id = f["id"]
            key_tag = f"[{f['fact_key']}] " if f.get("fact_key") else ""
            print(f"  #{fact_id}: {key_tag}{f['fact_value']}")
        print("Use '/forget <id>' to remove an item or '/forget all' to clear all.")
        print("--------------------------------------------------\n")

    def handle_remember(self, args: str) -> None:
        """Handles storing a persistent fact."""
        fact_text = args.strip()
        if not fact_text:
            print("\n[!] Usage: /remember <fact text>")
            print("    Example: /remember My favorite fruit is Mango\n")
            return

        fact_key = None
        if fact_text.startswith("[") and "]" in fact_text:
            end_bracket = fact_text.index("]")
            fact_key = fact_text[1:end_bracket].strip()
            fact_text = fact_text[end_bracket + 1:].lstrip(": ").strip()

        fact_id = self.brain.remember_fact(fact_text, fact_key)
        print(f"\n[+] Saved to persistent memory (ID #{fact_id}): {fact_text}\n")

    def handle_forget(self, args: str) -> None:
        """Handles deleting a persistent fact."""
        target = args.strip().lower()
        if not target:
            print("\n[!] Usage: /forget <id> or /forget all")
            print("    Use '/memory' to see IDs.\n")
            return

        if target == "all":
            count = self.brain.clear_all_facts()
            print(f"\n[-] Erased all {count} facts from persistent memory.\n")
            return

        try:
            fact_id = int(target)
            if self.brain.forget_fact(fact_id):
                print(f"\n[-] Removed fact #{fact_id} from persistent memory.\n")
            else:
                print(f"\n[!] Fact #{fact_id} not found in memory.\n")
        except ValueError:
            print("\n[!] Invalid ID. Please specify a numeric ID or 'all'.\n")

    def display_sessions(self) -> None:
        """Displays recent conversation sessions from SQLite."""
        sessions = self.brain.memory.get_recent_sessions(limit=5)
        print(f"\n--- Recent Sessions ({len(sessions)} found) ---")
        for s in sessions:
            current_tag = " (active)" if s["id"] == self.brain.memory.current_session_id else ""
            print(f"  [{s['id']}]{current_tag}: {s['title']} - {s['message_count']} messages ({s['updated_at']})")
        print("Use '/new' to start a fresh session.\n")

    def display_history(self) -> None:
        """Displays current in-memory session messages."""
        history = self.brain.get_history()
        print(f"\n--- Conversation History ({len(history)} messages, {self.brain.get_turn_count()} turns) ---")
        for idx, item in enumerate(history, 1):
            if isinstance(item, dict):
                role = item.get("role", "UNKNOWN").upper()
                content = item.get("content", "")
            else:
                role = getattr(item, "role", "UNKNOWN").upper()
                content = getattr(item, "content", "") or ""

            if role == "SYSTEM" and len(content) > 80:
                content = content[:77] + "..."
            print(f"[{idx}] {role}: {content}")
        print("--------------------------------------------------\n")

    def display_voices(self) -> None:
        """Displays list of available recommended voices."""
        voices = self.voice.get_available_voices()
        current_speaker = self.voice.get_speaker()
        print("\n--- Available Neural Voices ---")
        for voice_id, desc in voices.items():
            active_marker = " [ACTIVE]" if voice_id == current_speaker else ""
            print(f"  * {voice_id}{active_marker}")
            print(f"    {desc}")
        print("\nUse '/voice speaker <id>' to switch voice.")
        print("-------------------------------\n")

    def handle_voice_toggle(self, args: str) -> None:
        """Handles toggling or configuring voice output."""
        clean_args = args.strip()

        if not clean_args:
            new_state = self.voice.toggle()
            status = "enabled (Auto-Speak)" if new_state else "disabled (Text-Only)"
            print(f"\n[*] Voice output {status}.\n")
            return

        parts = clean_args.split(maxsplit=1)
        subcommand = parts[0].lower()

        if subcommand == "on":
            self.voice.toggle(True)
            print("\n[+] Voice output enabled. DUDE will speak every response automatically.\n")
        elif subcommand == "off":
            self.voice.toggle(False)
            print("\n[-] Voice output disabled. DUDE is now in text-only mode.\n")
        elif subcommand == "speaker":
            if len(parts) < 2 or not parts[1].strip():
                print("\n[!] Usage: /voice speaker <voice_id>")
                print("    Type '/voices' to view options.\n")
                return
            new_voice = parts[1].strip()
            self.voice.set_speaker(new_voice)
            print(f"\n[+] Active speaker set to: {new_voice}\n")
        else:
            print(f"\n[!] Unknown voice option: '{subcommand}'. Use 'on', 'off', or 'speaker <id>'.\n")

    def handle_speak(self, args: str) -> None:
        """Manually speaks the given text aloud."""
        text = args.strip()
        if not text:
            print("\n[!] Usage: /speak <text to speak aloud>\n")
            return

        print(f"\n[*] Speaking: \"{text}\"")
        self.voice.speak(text)
        print()

    def handle_talk(self, args: str) -> None:
        """
        Voice Input: Records microphone input, transcribes via Groq Whisper,
        and generates a conversational response from DUDE.
        """
        duration = 5.0
        clean_args = args.strip()
        if clean_args:
            try:
                duration = max(1.0, min(30.0, float(clean_args)))
            except ValueError:
                duration = 5.0

        if not self.voice.is_microphone_available():
            print("\n[!] No active microphone detected. Please plug in a microphone and try again.\n")
            return

        print(f"\n[MIC] Listening for {duration:.1f}s... (Speak into your mic now!)")
        try:
            user_speech = self.voice.listen(duration=duration)
        except VoiceRecordingError as e:
            print(f"\n[!] Recording Error: {e}\n")
            return
        except VoiceTranscriptionError as e:
            print(f"\n[!] Whisper Transcription Error: {e}\n")
            return

        if not user_speech:
            print("[!] No speech detected. Try again.\n")
            return

        print(f"\nYou (Voice): {user_speech}")
        self._process_message_and_respond(user_speech, force_speak=True)

    def handle_call(self) -> None:
        """
        Continuous Hands-Free Voice Call Mode.
        Automatically loops: Listen -> Transcribe -> Respond -> Speak -> Repeat.
        Say 'goodbye', 'exit', or press Ctrl+C to return to typing mode.
        """
        if not self.voice.is_microphone_available():
            print("\n[!] No active microphone detected. Cannot start hands-free voice call.\n")
            return

        print("\n" + "=" * 58)
        print("  [CALL] HANDS-FREE VOICE CALL CONNECTED")
        print("  Speak naturally! DUDE will answer with voice and keep listening.")
        print("  Say 'goodbye' or press Ctrl+C to exit call mode.")
        print("=" * 58 + "\n")

        self.voice.speak("Hey! Hands-free voice call connected. What's on your mind?")

        while True:
            try:
                print("\n[MIC] Listening... (Speak now!)")
                speech = self.voice.listen(duration=5.0)

                if not speech:
                    continue

                print(f"\nYou (Voice): {speech}")
                clean_lower = speech.lower().strip()

                if clean_lower in ("exit", "quit", "goodbye", "bye", "bye bye", "stop", "end call", "hang up"):
                    farewell = "Ending hands-free call. Talk to you soon!"
                    print(f"\nDUDE: {farewell}\n")
                    self.voice.speak(farewell)
                    break

                self._process_message_and_respond(speech, force_speak=True)

            except KeyboardInterrupt:
                print("\n\n[CALL] Voice call ended.\n")
                break
            except (VoiceRecordingError, VoiceTranscriptionError) as e:
                print(f"\n[!] Voice Error: {e}")
                continue

    def _process_message_and_respond(self, user_input: str, force_speak: bool = False) -> None:
        """Processes a message through the brain and handles tool notifications & speech."""
        initial_fact_count = len(self.brain.get_facts())
        print("\nDUDE: Thinking...", end="\r", flush=True)

        try:
            response = self.brain.generate_response(user_input)
            current_facts = self.brain.get_facts()

            sys.stdout.write("\033[K")
            if len(current_facts) > initial_fact_count:
                for f in current_facts[initial_fact_count:]:
                    print(f"[+] Saved to SQLite memory: {f['fact_value']}")

            print(f"DUDE: {response}\n")

            # Speak response if voice is enabled or if invoked via voice mode
            if force_speak or self.voice.enabled:
                self.voice.speak(response)

        except DudeAuthenticationError as e:
            sys.stdout.write("\033[K")
            print(f"\n[!] AUTHENTICATION ERROR: {e}\n")
        except DudeRateLimitError as e:
            sys.stdout.write("\033[K")
            print(f"\n[!] RATE LIMIT ERROR: {e}\n")
        except DudeConnectionError as e:
            sys.stdout.write("\033[K")
            print(f"\n[!] CONNECTION ERROR: {e}\n")
        except (DudeAPIError, DudeBrainError) as e:
            sys.stdout.write("\033[K")
            print(f"\n[!] ERROR: {e}\n")
        except ValueError as e:
            sys.stdout.write("\033[K")
            print(f"\n[!] INPUT ERROR: {e}\n")
        except Exception as e:
            sys.stdout.write("\033[K")
            print(f"\n[!] UNEXPECTED ERROR: {e}\n")

    def run(self) -> None:
        """
        Main chat loop. Continues until user exits.
        """
        self.display_banner()

        while True:
            try:
                user_input = input("You: ").strip()

                # Pressing Enter on an empty line triggers microphone recording immediately
                if not user_input:
                    if self.voice.is_microphone_available():
                        print("[MIC] Quick-talk activated (Empty Enter). Speak now!")
                        self.handle_talk("")
                    continue

                # Strip accidental 'You: ' prefix if pasted or typed
                if user_input.lower().startswith("you:"):
                    user_input = user_input[4:].strip()
                elif user_input.lower().startswith("you :"):
                    user_input = user_input[5:].strip()

                if not user_input:
                    continue

                lower_input = user_input.lower()

                # Core exit commands
                if lower_input in ("/exit", "/quit", "exit", "quit"):
                    print("\nDUDE: Goodbye! Have a great day.\n")
                    break

                if lower_input == "/help":
                    self.display_help()
                    continue

                # Tool direct shortcuts
                if lower_input == "/stats":
                    self.display_system_stats()
                    continue

                if lower_input.startswith("/open"):
                    self.handle_open(user_input[5:])
                    continue

                if lower_input == "/notes":
                    self.display_notes()
                    continue

                # Hands-free continuous voice call mode
                if lower_input in ("/call", "/live", "/phone", "call"):
                    self.handle_call()
                    continue

                # Voice commands
                if lower_input.startswith(("/talk", "/listen")):
                    arg = user_input[5:].strip() if lower_input.startswith("/talk") else user_input[7:].strip()
                    self.handle_talk(arg)
                    continue

                if lower_input.startswith("/voice"):
                    self.handle_voice_toggle(user_input[6:])
                    continue

                if lower_input == "/voices":
                    self.display_voices()
                    continue

                if lower_input.startswith("/speak"):
                    self.handle_speak(user_input[6:])
                    continue

                # Memory commands
                if lower_input == "/memory":
                    self.display_memory()
                    continue

                if lower_input.startswith("/remember"):
                    self.handle_remember(user_input[9:])
                    continue

                if lower_input.startswith("/forget"):
                    self.handle_forget(user_input[7:])
                    continue

                # Session commands
                if lower_input == "/sessions":
                    self.display_sessions()
                    continue

                if lower_input in ("/new", "/clear"):
                    self.brain.start_new_session("Fresh Session")
                    print("\n[!] Started a fresh session. (Persistent facts remain saved!)\n")
                    continue

                if lower_input == "/history":
                    self.display_history()
                    continue

                # Standard text conversation (processes tools autonomously & speaks reply)
                self._process_message_and_respond(user_input, force_speak=False)

            except KeyboardInterrupt:
                print("\n\nDUDE: Session interrupted. Goodbye!\n")
                break
            except EOFError:
                print("\n\nDUDE: Exiting. Goodbye!\n")
                break
            except Exception as e:
                print(f"\n[!] UNEXPECTED ERROR: {e}\n")
