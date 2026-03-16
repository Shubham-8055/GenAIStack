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

            # Extract valid JSON block to bypass <think> tags or markdown
            cleaned_content = content.strip()
            start_idx = cleaned_content.find('{')
            end_idx = cleaned_content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                cleaned_content = cleaned_content[start_idx:end_idx+1]

            print(f"[Guardrails] RAW LLM OUTPUT (Cleaned): {cleaned_content!r}")
            data = json.loads(cleaned_content)

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
