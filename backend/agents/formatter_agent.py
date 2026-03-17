"""
Formatter Agent — Config-driven data formatter.
Accepts prompt and LLM instance from project config.
"""
from langchain_core.messages import SystemMessage, HumanMessage
from backend.core.utils import strip_think_tags


class DataFormatterAgent:
    def __init__(self, system_prompt: str, llm):
        """
        Args:
            system_prompt: The formatter system prompt (loaded from DB config).
            llm: A ChatOpenAI instance (created via llm_provider).
        """
        self.llm = llm
        self.system_prompt = system_prompt
        print("[Formatter] Agent initialized (config-driven).")

    def format_response(self, text: str, instructions: str = "format as structured text") -> str:
        """Format the given text based on instructions."""
        try:
            print(f"[Formatter] Formatting with instruction: '{instructions}'")
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"INSTRUCTION: {instructions}\n\nDATA:\n{text}"),
            ]
            response = self.llm.invoke(messages)
            return strip_think_tags(response.content)

        except Exception as e:
            print(f"[Formatter] Error: {e}")
            return text  # Fallback to original text
