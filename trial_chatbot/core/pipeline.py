"""
Pipeline — Runs the full agent chain with hardcoded config.
"""
import time
import json
import os
from langchain_openai import ChatOpenAI


def get_llm(config: dict):
    """Create LLM instance from config."""
    return ChatOpenAI(
        openai_api_base=os.getenv("LLM_BASE_URL", "http://localhost:8080/v1"),
        openai_api_key=os.getenv("LLM_API_KEY", "not-needed"),
        model_name=config.get("model_name", "/model"),
        temperature=config.get("temperature", 0.0),
    )


def run_pipeline(user_query: str, chat_history: list, config: dict) -> dict:
    """Run the full agent pipeline."""
    start_time = time.time()
    answer = ""
    used_rag = False
    agent_path = []

    llm = get_llm(config)

    # 1. Guardrails
    if config.get("enable_guardrail"):
        agent_path.append("guardrails")
        from agents.guardrails_agent import GuardrailsAgent
        guard = GuardrailsAgent(system_prompt=config["guardrail_prompt"], llm=llm)
        is_safe, rejection = guard.check(user_query)
        if not is_safe:
            return {"answer": rejection, "used_rag": False,
                     "agent_path": ["guardrails"], "latency": round(time.time() - start_time, 3)}

    # 2. Orchestrator routing
    agent_path.append("orchestrator")

    # Dynamic tool agent injection
    orchestrator_prompt = config["orchestrator_prompt"]
    if config.get("enable_tool_agent"):
        tool_section = """
3. `transaction_agent`
Use this when the user query involves checking a transaction status,
looking up a payment/transfer, or finding transaction details by date, amount, or ID.
Inputs: {"query": "the original user query"}
"""
        if "### STRICT DECISION RULES" in orchestrator_prompt:
            orchestrator_prompt = orchestrator_prompt.replace(
                "### STRICT DECISION RULES",
                tool_section + "\n### STRICT DECISION RULES"
            )

    from core.orchestrator import MainOrchestrator
    orchestrator = MainOrchestrator(
        system_prompt=orchestrator_prompt,
        rag_prompt=config["rag_prompt"],
        llm=llm,
    )
    command = orchestrator.execute(user_query, chat_history)
    target = command.get("target", "error")
    params = command.get("parameters", {})

    # 3. Route to agents
    if target == "rag_agent" and config.get("enable_rag"):
        agent_path.append("rag_agent")
        used_rag = True
        from agents.rag_agent import RAGAgent
        rag = RAGAgent(top_k=config.get("top_k", 4))
        query = params.get("query", user_query)
        rag_result = rag.execute(query)
        context_text = rag_result.get("context_text", "")

        agent_path.append("synthesizer")
        answer = orchestrator.synthesize_answer(user_query, context_text)

        fmt_instruction = params.get("formatting_instruction", "")
        if config.get("enable_formatter") and fmt_instruction:
            agent_path.append("formatter")
            from agents.formatter_agent import DataFormatterAgent
            formatter = DataFormatterAgent(system_prompt=config["formatter_prompt"], llm=llm)
            answer = formatter.format_response(answer, fmt_instruction)

    elif target == "direct_response":
        agent_path.append("direct_response")
        answer = params.get("message", "I am not sure how to respond.")
    else:
        answer = "I encountered an error processing your request."

    latency = round(time.time() - start_time, 3)
    return {"answer": answer, "used_rag": used_rag, "agent_path": agent_path, "latency": latency}


def _query_local_transactions(extracted: dict, fields: list) -> list:
    """Query transactions from local CSV file."""
    import csv, os
    from datetime import datetime, timedelta

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "transactions.csv")
    if not os.path.exists(csv_path):
        return []

    results = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            match = True

            # Check amount
            if extracted.get("amount") is not None:
                try:
                    if float(row.get("amount", 0)) != float(extracted["amount"]):
                        match = False
                except (ValueError, TypeError):
                    match = False

            # Check date (fuzzy ±1 day)
            if extracted.get("date") and match:
                try:
                    txn_date = datetime.fromisoformat(row.get("txn_date", ""))
                    target_date = datetime.fromisoformat(extracted["date"])
                    if abs((txn_date.date() - target_date.date()).days) > 1:
                        match = False
                except (ValueError, TypeError):
                    pass

            # Check custom fields
            for field in fields:
                fname = field.get("name", "")
                fval = extracted.get(fname)
                if fval and match:
                    if str(row.get(fname, "")).lower() != str(fval).lower():
                        match = False

            if match:
                results.append(row)

    return results[:10]


def _format_local_results(rows: list, fields: list) -> str:
    """Format CSV query results."""
    if not rows:
        return "No matching transactions found."

    lines = ["Found **" + str(len(rows)) + "** matching transaction(s):\n"]
    for i, row in enumerate(rows, 1):
        status = row.get("status", "unknown").lower()
        emoji = {"success": "✅", "failed": "❌", "pending": "⏳"}.get(status, "❓")
        table_rows = ["| **Status** | " + emoji + " " + status.upper() + " |"]
        table_rows.append("| **Amount** | ₹" + str(row.get("amount", "")) + " |")
        table_rows.append("| **Date** | " + str(row.get("txn_date", "")) + " |")
        table_rows.append("| **Bank** | " + str(row.get("bank_name", "")) + " |")
        table_rows.append("| **RRN** | " + str(row.get("rrn", "")) + " |")
        for field in fields:
            fname = field.get("name", "")
            flabel = field.get("label", fname)
            table_rows.append("| **" + flabel + "** | " + str(row.get(fname, "N/A")) + " |")
        table_rows.append("| **Remarks** | " + str(row.get("remarks", "")) + " |")
        lines.append("### Transaction " + str(i) + "\n| Field | Details |\n|---|---|\n" + "\n".join(table_rows) + "\n")
    return "\n".join(lines)
