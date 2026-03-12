"""
Transaction Agent — Tool-call agent that queries the transactions table.
Uses the LLM to extract parameters from natural language,
then queries the database and returns formatted results.
Supports dynamic custom fields defined per project.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage


class TransactionAgent:
    def __init__(self, system_prompt: str, llm, tool_agent_fields: list = None):
        """
        Args:
            system_prompt: The parameter extraction prompt (from DB config).
            llm: A ChatOpenAI instance.
            tool_agent_fields: List of custom field defs [{name, label, ...}].
        """
        self.llm = llm
        self.system_prompt = system_prompt
        self.tool_agent_fields = tool_agent_fields or []
        print(f"[TransactionAgent] Initialized with {len(self.tool_agent_fields)} custom fields.")

    def build_extraction_prompt(self, user_query: str) -> list:
        """Build a dynamic extraction prompt based on configured fields."""
        # Start with fixed fields (date + amount)
        fields_desc = """You must extract the following parameters from the user query:

1. `date` — The date of the transaction in **YYYY-MM-DD** format.
   - "today" → use current date
   - "yesterday" → use yesterday's date
   - If not mentioned → set to null

2. `amount` — The transaction amount as a **number** (no currency symbols).
   - If not mentioned → set to null
"""
        # Add dynamic fields
        for i, field in enumerate(self.tool_agent_fields, start=3):
            fields_desc += f"""
{i}. `{field['name']}` — {field.get('label', field['name'])}
   - If not mentioned → set to null
"""

        # Build expected output format
        output_fields = '    "date": "YYYY-MM-DD or null",\n    "amount": 0'
        for field in self.tool_agent_fields:
            output_fields += f',\n    "{field["name"]}": "value or null"'

        full_prompt = f"""{self.system_prompt}

{fields_desc}

### RULES:
- Return ONLY valid JSON, nothing else.
- Do NOT answer the user's question.
- Even if only 1 parameter is found, still return all fields.

### OUTPUT FORMAT:
```json
{{
{output_fields}
}}
```"""

        return [
            SystemMessage(content=full_prompt),
            HumanMessage(content=user_query),
        ]

    def extract_params(self, user_query: str) -> dict:
        """Use the LLM to extract transaction lookup parameters."""
        messages = self.build_extraction_prompt(user_query)

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Clean JSON wrapper
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            params = json.loads(content.strip())
            print(f"[TransactionAgent] Extracted params: {params}")
            return params

        except Exception as e:
            print(f"[TransactionAgent] Param extraction error: {e}")
            result = {"date": None, "amount": None}
            for field in self.tool_agent_fields:
                result[field["name"]] = None
            return result

    def format_results(self, transactions: list) -> str:
        """Format transaction results into a readable response."""
        if not transactions:
            return ("No matching transactions found. Please check the details "
                    "and try again with the correct parameters.")

        result_lines = [f"Found **{len(transactions)}** matching transaction(s):\n"]

        for i, txn in enumerate(transactions, 1):
            status_emoji = {
                "success": "✅",
                "failed": "❌",
                "pending": "⏳",
            }.get(str(txn.status).lower(), "❓")

            rows = [
                f"| **Status** | {status_emoji} {txn.status.upper()} |",
                f"| **Amount** | ₹{txn.amount} |",
                f"| **Type** | {txn.txn_type.capitalize()} |",
                f"| **Date** | {txn.txn_date.strftime('%d %b %Y, %I:%M %p')} |",
                f"| **Bank** | {txn.bank_name} |",
                f"| **RRN** | {txn.rrn} |",
            ]

            # Add custom fields
            custom = txn.custom_fields or {}
            for field in self.tool_agent_fields:
                fname = field["name"]
                flabel = field.get("label", fname)
                fval = custom.get(fname, txn.aadhaar_last4 if fname == "aadhaar_last4" else "N/A")
                rows.append(f"| **{flabel}** | {fval} |")

            rows.append(f"| **Remarks** | {txn.remarks} |")

            result_lines.append(
                f"### Transaction {i}\n"
                f"| Field | Details |\n"
                f"|---|---|\n"
                + "\n".join(rows) + "\n"
            )

        return "\n".join(result_lines)
