"""
Shared utilities for the GenAI backend.
"""
import re


def strip_think_tags(text: str) -> str:
    """
    Remove <think>...</think> blocks from LLM output.

    Reasoning models (e.g. DeepSeek-R1) wrap their internal chain-of-thought
    inside <think> tags. This helper strips those blocks so only the clean,
    user-facing response is returned.

    Handles:
      - Multi-line think blocks
      - Nested or malformed tags (strips everything between first <think> and last </think>)
      - Leading/trailing whitespace left after removal
    """
    if not text:
        return text
    # Remove all <think>...</think> blocks (case-insensitive, non-greedy, dotall)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()
