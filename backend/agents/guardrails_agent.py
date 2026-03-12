"""
Guardrails Agent — Config-driven safety classifier.
Accepts prompt and LLM instance from project config (no hardcoded values).
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage


class GuardrailsAgent:
    def __init__(self, system_prompt: str, llm):
        """
        Args:
            system_prompt: The guardrail system prompt (loaded from DB config).
            llm: A ChatOpenAI instance (created via llm_provider).
        """
        self.llm = llm
        self.system_prompt = system_prompt
        print("[Guardrails] Agent initialized (config-driven).")

    def check(self, user_query: str, chat_history: list = None) -> dict:
        """
        Classify a query as allowed or blocked.
        
        Returns:
            dict: {"status": "allowed"} OR {"status": "blocked", "topic": "...", "message": "..."}
        """
        try:
            # Build context string from history
            context_str = ""
            if chat_history:
                recent = chat_history[-4:]
                context_str = "\n".join(
                    [f"{msg['role'].upper()}: {msg['content']}" for msg in recent]
                )

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Context:\n{context_str}\n\nUser Query: {user_query}"),
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Clean markdown JSON wrapper
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content.strip())

            status = data.get("status", "unknown").upper()
            if status == "BLOCKED":
                print(f"[Guardrails] BLOCKED (Topic: {data.get('topic', 'Unknown')})")
            else:
                print(f"[Guardrails] ALLOWED")

            return data

        except Exception as e:
            # Fail-safe: Default to ALLOW on transient errors
            print(f"[Guardrails] Error: {e} — defaulting to ALLOWED")
            return {"status": "allowed"}
