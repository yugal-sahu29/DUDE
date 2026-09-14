"""
Core AI Brain for DUDE (Powered by Groq).
Manages session conversation history, persistent memory, autonomous system tools,
and communicates with the Groq API.
"""

import json
from typing import List, Dict, Any, Optional, Callable
import groq  # type: ignore
from groq import Groq  # type: ignore

from dude.config import Config
from dude.core.prompts import DEFAULT_SYSTEM_PROMPT, build_system_prompt
from dude.memory.manager import MemoryManager
from dude.tools.registry import ToolRegistry
from dude.tools.system import get_default_registry


class DudeBrainError(Exception):
    """Base exception for brain errors."""
    pass


class DudeAuthenticationError(DudeBrainError):
    """Raised when API credentials are rejected."""
    pass


class DudeRateLimitError(DudeBrainError):
    """Raised when Groq rate limit or quota is exceeded."""
    pass


class DudeConnectionError(DudeBrainError):
    """Raised when network or connectivity issues prevent API calls."""
    pass


class DudeAPIError(DudeBrainError):
    """Raised when the Groq API returns an unexpected error."""
    pass


class DudeBrain:
    """
    Encapsulates the conversational AI engine for DUDE.
    Coordinates persistent SQLite memory, autonomous system tools,
    and communicates with Groq.
    """

    def __init__(
        self,
        config: Config,
        system_prompt: Optional[str] = None,
        memory: Optional[MemoryManager] = None,
        tools: Optional[ToolRegistry] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self.config = config
        self.base_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.memory = memory or MemoryManager()
        self.tools = tools if tools is not None else get_default_registry()
        self.on_tool_call = on_tool_call

        # Initialize the Groq client
        self.client = Groq(api_key=self.config.api_key)

        # Session conversation history
        self._history: List[Any] = []
        self._initialize_history()

    def _get_active_system_prompt(self) -> str:
        """Builds system prompt injected with active long-term facts."""
        facts_block = self.memory.format_facts_for_prompt()
        return build_system_prompt(self.base_prompt, facts_block)

    def _initialize_history(self) -> None:
        """Resets the in-memory history with the current active system prompt."""
        self._history = [
            {"role": "system", "content": self._get_active_system_prompt()}
        ]

    def _sync_system_prompt(self) -> None:
        """Updates the system prompt in the active history when memory changes."""
        if self._history and isinstance(self._history[0], dict) and self._history[0].get("role") == "system":
            self._history[0]["content"] = self._get_active_system_prompt()

    # ---------------------------------------------------------
    # Persistent Memory Helpers
    # ---------------------------------------------------------

    def remember_fact(self, fact_value: str, fact_key: Optional[str] = None) -> int:
        """Saves a fact into persistent memory and updates active prompt."""
        fact_id = self.memory.add_fact(fact_value, fact_key)
        self._sync_system_prompt()
        return fact_id

    def get_facts(self) -> List[Dict[str, Any]]:
        """Returns all persistent facts stored in memory."""
        return self.memory.get_facts()

    def forget_fact(self, fact_id: int) -> bool:
        """Removes a specific fact from memory and updates active prompt."""
        removed = self.memory.delete_fact(fact_id)
        if removed:
            self._sync_system_prompt()
        return removed

    def clear_all_facts(self) -> int:
        """Erases all persistent facts from memory."""
        count = self.memory.clear_all_facts()
        self._sync_system_prompt()
        return count

    def start_new_session(self, title: str = "Chat Session") -> str:
        """Starts a fresh session while retaining persistent user facts."""
        session_id = self.memory.start_new_session(title)
        self._initialize_history()
        return session_id

    def clear_history(self) -> None:
        """Clears in-session history and starts a fresh session."""
        self.start_new_session("Fresh Session")

    def get_history(self) -> List[Any]:
        """Returns a copy of the current in-memory history."""
        return list(self._history)

    def get_turn_count(self) -> int:
        """Returns the number of user/assistant conversational turns in active session."""
        count = 0
        for m in self._history:
            if isinstance(m, dict):
                if m.get("role") in ("user", "assistant"):
                    count += 1
            elif getattr(m, "role", None) in ("user", "assistant"):
                count += 1
        return count

    # ---------------------------------------------------------
    # Inference & Autonomous Response Generation
    # ---------------------------------------------------------

    def generate_response(self, user_message: str) -> str:
        """
        Sends a user message along with session history and system tools to Groq.
        Autonomously executes any requested tool calls and returns DUDE's response.

        Raises:
            ValueError: If user_message is empty.
            DudeAuthenticationError: If API key is invalid or unauthorized.
            DudeRateLimitError: If rate limit or quota exceeded.
            DudeConnectionError: If network error occurs.
            DudeAPIError: If any other Groq API error occurs.
        """
        clean_input = user_message.strip()
        if not clean_input:
            raise ValueError("Input message cannot be empty.")

        # Automatically extract and persist facts from natural conversation
        new_facts = self.memory.auto_extract_facts(clean_input)
        if new_facts:
            self._sync_system_prompt()

        # Save history checkpoint for atomic rollback on failure
        history_snapshot = list(self._history)

        # Stage user message into history
        user_entry = {"role": "user", "content": clean_input}
        self._history.append(user_entry)

        try:
            max_tool_rounds = 3
            rounds = 0

            while rounds < max_tool_rounds:
                rounds += 1
                call_kwargs: Dict[str, Any] = {
                    "model": self.config.model,
                    "messages": list(self._history),
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }

                # Provide tools schema on first round
                if self.tools and self.tools.has_tools() and rounds == 1:
                    call_kwargs["tools"] = self.tools.get_schemas()
                    call_kwargs["tool_choice"] = "auto"

                response = self.client.chat.completions.create(**call_kwargs)
                message = response.choices[0].message

                # Check if model requested tool calls
                tool_calls = getattr(message, "tool_calls", None)
                if tool_calls and isinstance(tool_calls, (list, tuple)) and len(tool_calls) > 0:
                    # Append assistant message containing tool calls
                    self._history.append(message)

                    for tc in tool_calls:
                        call_id = tc.id
                        func_name = tc.function.name

                        try:
                            args = (
                                json.loads(tc.function.arguments)
                                if isinstance(tc.function.arguments, str)
                                else (tc.function.arguments or {})
                            )
                        except Exception:
                            args = {}

                        # Notify callback if registered
                        if self.on_tool_call:
                            self.on_tool_call(func_name, args)

                        # Execute tool
                        result = self.tools.execute(func_name, args)

                        # Append tool response
                        self._history.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": result,
                        })

                    # Loop continues to send tool output back to model for final reply
                    continue
                else:
                    # Model provided text answer
                    assistant_reply = message.content or ""
                    self._history.append({"role": "assistant", "content": assistant_reply})

                    # Persist turn into SQLite database
                    self.memory.record_message("user", clean_input)
                    self.memory.record_message("assistant", assistant_reply)

                    return assistant_reply

            # Fallback if max tool rounds reached
            fallback_reply = "I completed the requested system tasks."
            self._history.append({"role": "assistant", "content": fallback_reply})
            self.memory.record_message("user", clean_input)
            self.memory.record_message("assistant", fallback_reply)
            return fallback_reply

        except groq.AuthenticationError as e:
            self._history = history_snapshot
            raise DudeAuthenticationError(
                "Authentication failed: The provided Groq API key is invalid or expired. "
                "Please verify your GROQ_API_KEY in the .env file."
            ) from e

        except groq.NotFoundError as e:
            self._history = history_snapshot
            raise DudeAPIError(
                f"Model '{self.config.model}' was not found on Groq. "
                "Please check GROQ_MODEL in your .env file."
            ) from e

        except groq.RateLimitError as e:
            self._history = history_snapshot
            raise DudeRateLimitError(
                "Groq rate limit reached: Try again in a few seconds or reduce GROQ_MAX_TOKENS in .env."
            ) from e

        except groq.APIConnectionError as e:
            self._history = history_snapshot
            raise DudeConnectionError(
                "Network connection error: Unable to reach the Groq servers. "
                "Please check your internet connection and try again."
            ) from e

        except groq.APIError as e:
            self._history = history_snapshot
            raise DudeAPIError(
                f"Groq API error ({getattr(e, 'code', 'unknown')}): {e.message}"
            ) from e

        except Exception as e:
            self._history = history_snapshot
            raise DudeBrainError(f"Unexpected error communicating with AI brain: {str(e)}") from e
