"""
System prompts and persona definitions for DUDE.
"""

DEFAULT_SYSTEM_PROMPT = (
    "You are DUDE, an intelligent, helpful, and versatile personal AI assistant. "
    "You communicate clearly, concisely, and naturally. "
    "You maintain conversation context, provide accurate and direct answers, "
    "and have a friendly, capable personality. "
    "When explaining technical or complex concepts, keep explanations intuitive and well-structured."
)


def build_system_prompt(base_prompt: str = DEFAULT_SYSTEM_PROMPT, memory_context: str = "") -> str:
    """Combines base persona prompt with active persistent memory facts."""
    if not memory_context.strip():
        return base_prompt
    return f"{base_prompt}\n\n{memory_context.strip()}"
