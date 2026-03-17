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

            import re
            
            # Extract valid JSON block to bypass <think> tags or markdown
            cleaned_content = content.strip()
            start_idx = cleaned_content.find('{')
            end_idx = cleaned_content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = cleaned_content[start_idx:end_idx+1]
            else:
                json_str = cleaned_content

            print(f"[Guardrails] RAW LLM OUTPUT (Cleaned): {json_str!r}")
            
            try:
                data = json.loads(json_str)
            except Exception as e:
                # Regex fallback for corrupted JSON (e.g. "Extra data" from multiple blocks)
                print(f"[Guardrails] JSON Error ({e}). Attempting regex extraction.")
                status_match = re.search(r'"status"\s*:\s*"([^"]+)"', content, re.IGNORECASE)
                topic_match = re.search(r'"topic"\s*:\s*"([^"]+)"', content, re.IGNORECASE)
                
                data = {
                    "status": status_match.group(1).lower() if status_match else "allowed",
                    "topic": topic_match.group(1) if topic_match else "Unknown"
                }

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
