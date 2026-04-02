"""Formatter Agent — Formats responses according to instructions."""
from langchain_core.messages import SystemMessage, HumanMessage


class DataFormatterAgent:
    def __init__(self, system_prompt: str, llm):
        self.llm = llm
        self.system_prompt = system_prompt

    def format_response(self, raw_answer: str, instruction: str) -> str:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Formatting instruction: {instruction}\n\nContent to format:\n{raw_answer}"),
        ]
        try:
            return self.llm.invoke(messages).content
        except Exception:
            return raw_answer
