"""Guardrails Agent — Validates user queries for safety."""
import json
from langchain_core.messages import SystemMessage, HumanMessage


class GuardrailsAgent:
    def __init__(self, system_prompt: str, llm):
        self.llm = llm
        self.system_prompt = system_prompt

    def check(self, user_query: str) -> tuple:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_query),
        ]
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content.strip())
            is_safe = result.get("is_safe", True)
            message = result.get("message", "")
            return is_safe, message
        except Exception:
            return True, ""
