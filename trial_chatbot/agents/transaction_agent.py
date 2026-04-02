"""Transaction Agent — Extracts params from queries and formats results."""
import json
from langchain_core.messages import SystemMessage, HumanMessage


class TransactionAgent:
    def __init__(self, system_prompt: str, llm, tool_agent_fields: list = None):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tool_agent_fields = tool_agent_fields or []

    def extract_params(self, user_query: str) -> dict:
        fields_desc = """Extract these parameters:
1. `date` — YYYY-MM-DD format. "today" = current date. null if not mentioned.
2. `amount` — Number only, no currency. null if not mentioned.
"""
        for i, field in enumerate(self.tool_agent_fields, start=3):
            fields_desc += f"{i}. `{field['name']}` — {field.get('label', field['name'])}. null if not mentioned.\n"

        output_fields = '    "date": "YYYY-MM-DD or null",\n    "amount": 0'
        for field in self.tool_agent_fields:
            output_fields += f',\n    "{field["name"]}": "value or null"'

        prompt = f"""{self.system_prompt}
{fields_desc}
Return ONLY valid JSON:
```json
{{
{output_fields}
}}
```"""
        messages = [SystemMessage(content=prompt), HumanMessage(content=user_query)]
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"[TransactionAgent] Error: {e}")
            result = {"date": None, "amount": None}
            for f in self.tool_agent_fields:
                result[f["name"]] = None
            return result
