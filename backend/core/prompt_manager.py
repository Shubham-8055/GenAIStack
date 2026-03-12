"""
Prompt Manager — DEPRECATED.
All prompts are now stored in PostgreSQL and loaded via agent_configs.
Default prompts are defined in backend/db/crud.py.

This file is kept only for backward compatibility.
"""
from backend.db.crud import (
    get_default_orchestrator_prompt,
    get_default_guardrail_prompt,
    get_default_rag_prompt,
    get_default_formatter_prompt,
)


# Legacy function — delegates to crud.py defaults
def get_orchestrator_prompt():
    return get_default_orchestrator_prompt()
