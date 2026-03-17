"""
Agent Engine — Unified pipeline runner.
The heart of the GenAI platform. Loads project config from DB,
instantiates agents on-the-fly, and runs the full pipeline.
"""
import time
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import crud
from backend.services.llm_provider import get_llm
from backend.agents.guardrails_agent import GuardrailsAgent
from backend.agents.rag_agent import RAGAgent
from backend.agents.formatter_agent import DataFormatterAgent
from backend.agents.transaction_agent import TransactionAgent
from backend.core.orchestrator import MainOrchestrator
from backend.core.external_db import query_external_db, format_external_results


async def run_pipeline(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_query: str,
    chat_history: list = None,
) -> dict:
    """
    Run the full agent pipeline for a project.

    Steps:
        1. Load agent config from DB
        2. Create LLM instance
        3. Run guardrails (if enabled)
        4. Route via orchestrator
        5. Call RAG agent (if enabled and routed)
        6. Synthesize answer
        7. Format via formatter (if enabled)
        8. Log to query_logs
        9. Return structured response

    Returns:
        dict: {answer, used_rag, agent_path, latency, retrieved_chunks}
    """
    start_time = time.time()
    
    print("\n" + "=" * 80)
    print(f"[{project_id}] 👤 USER QUERY: {user_query}")
    print(f"[{project_id}] 🤖 INITIATING AGENT PIPELINE...")
    print("-" * 80)
    chat_history = chat_history or []
    agent_path = []
    used_rag = False
    retrieved_chunks = []
    answer = ""

    # 1. Load project config
    config = await crud.get_agent_config(db, project_id)
    if not config:
        return _error_response("Project config not found.", start_time)

    # 2. Create LLM
    llm = get_llm(
        model_name=config.model_name,
        temperature=config.temperature,
    )

    # 3. Guardrails check
    if config.enable_guardrail:
        agent_path.append("guardrails")
        guard = GuardrailsAgent(system_prompt=config.guardrail_prompt, llm=llm)
        guard_result = guard.check(user_query, chat_history)

        if guard_result.get("status") == "blocked":
            answer = guard_result.get("message", "I cannot answer that.")
            latency = round(time.time() - start_time, 3)

            # Log blocked query
            await crud.create_query_log(
                db=db,
                project_id=project_id,
                query=user_query,
                final_answer=answer,
                agent_path=agent_path,
                used_rag=False,
                latency=latency,
                retrieved_chunks=[],
            )

            return {
                "answer": answer,
                "used_rag": False,
                "agent_path": agent_path,
                "latency": latency,
                "retrieved_chunks": [],
            }

    # 4. Route via orchestrator
    agent_path.append("orchestrator")

    # Dynamically inject transaction_agent into orchestrator prompt if tool agent is enabled
    orchestrator_prompt = config.orchestrator_prompt
    if config.enable_tool_agent:
        # Append transaction_agent as a routing target
        # Build dynamic clarification phrase based on project fields
        field_labels = [f.get("label", f.get("name", "")) for f in (config.tool_agent_fields or [])]
        if field_labels:
            fields_desc = "transaction amount, date, and " + ", ".join(field_labels).lower()
        else:
            fields_desc = "transaction amount and date"
        
        clarification_msg = f"Could you please provide the {fields_desc}?"

        tool_agent_section = f"""

3. `transaction_agent`
Use this ONLY when the user provides SPECIFIC transaction details such as:
- A specific date ("yesterday", "10th March", etc.)
- A specific amount ("₹5000", "5000 rupees")
- Any specific identifier like {', '.join(field_labels) if field_labels else 'RRN'}
- A combination of the above to look up a specific transaction

Do NOT use this for vague requests like "show my transactions", "need txn info", or "transaction history".
For vague requests where details are missing, route to `direct_response` and explicitly ask the user to provide the specific mandatory fields required for this project: **{fields_desc}**.
Formulate your JSON exactly like this:
```json
{{
    "thought": "User has a vague transaction issue. I need to ask them for the necessary details ({fields_desc}).",
    "target": "direct_response",
    "parameters": {{
        "message": "Could you please provide the transaction details, specifically the {fields_desc}, so I can assist you better?"
    }}
}}
```

Inputs:
- `query`: The original user query (the agent will extract params itself).

Example:
Example:
{{
    "thought": "User is asking about a specific transaction status.",
    "target": "transaction_agent",
    "parameters": {{
        "query": "Check status of 5000 transaction done yesterday, Aadhaar ending 1234"
    }}
}}
"""
        # Insert before the STRICT DECISION RULES section
        if "### STRICT DECISION RULES" in orchestrator_prompt:
            orchestrator_prompt = orchestrator_prompt.replace(
                "### STRICT DECISION RULES",
                tool_agent_section + "\n### STRICT DECISION RULES"
            )
            # Also add the transaction routing rule
            orchestrator_prompt = orchestrator_prompt.replace(
                "When in doubt",
                f"If the question is about checking a SPECIFIC transaction with details (date, amount, etc.) → use `transaction_agent`.\nIf the user asks vaguely about transactions without specific details → use `direct_response` and ask them to provide their {fields_desc}.\nWhen in doubt"
            )
        else:
            # Fallback: just append to the end
            orchestrator_prompt += tool_agent_section

    # Force strict JSON start to prevent API 500 errors with reasoning models
    orchestrator_prompt += """\n\nCRITICAL JSON IMMUTABLE STRUCTURE:
You MUST ONLY output a single, valid JSON object. 
If you are responding to a greeting like 'hi' or just need to talk to the user directly, DO NOT output raw text. You MUST use this EXACT format:
```json
{{
    "thought": "User is greeting or needs a direct reply. I will respond warmly.",
    "target": "direct_response",
    "parameters": {{
        "message": "Hello! How can I help you today?"
    }}
}}
```
Your entire reasoning MUST go inside the `"thought"` key.
Your response MUST start with exactly `{` and end with `}`."""

    orchestrator = MainOrchestrator(
        system_prompt=orchestrator_prompt,
        rag_prompt=config.rag_prompt,
        llm=llm,
    )
    command = orchestrator.execute(user_query, chat_history)
    target = command.get("target", "error")
    params = command.get("parameters", {})

    # Normalize target aliases so the LLM can use either name
    if target in ("transaction_lookup_agent", "transaction_lookup", "tool"):
        target = "transaction_agent"
        print(f"[AgentEngine] Normalized target to 'transaction_agent'")
    elif target in ("ask_details", "clarification"):
        target = "direct_response"
        print(f"[AgentEngine] Normalized target to 'direct_response'")
    elif target == "rag":
        target = "rag_agent"
        print(f"[AgentEngine] Normalized target to 'rag_agent'")

    print(f"[AgentEngine] Target: {target}, Params: {params}")

    # 5. Execute based on routing decision
        
    if target == "rag_agent" and config.enable_rag:
        agent_path.append("rag_agent")
        used_rag = True

        # Create project-specific RAG agent
        collection_name = f"project_{project_id}"
        rag = RAGAgent(collection_name=collection_name, top_k=config.top_k)

        query = params.get("query", user_query)
        rag_result = rag.execute(query)

        context_text = rag_result.get("context_text", "")
        retrieved_chunks = rag_result.get("chunks", [])

        # Synthesize answer from context
        agent_path.append("synthesizer")
        answer = orchestrator.synthesize_answer(user_query, context_text)

        # Format if enabled
        fmt_instruction = params.get("formatting_instruction", "")
        if config.enable_formatter and fmt_instruction:
            agent_path.append("formatter")
            formatter = DataFormatterAgent(system_prompt=config.formatter_prompt, llm=llm)
            answer = formatter.format_response(answer, fmt_instruction)

    elif target == "transaction_agent" and config.enable_tool_agent:
        agent_path.append("transaction_agent")

        # Get configured fields
        fields = config.tool_agent_fields or []

        # Use the tool agent to extract params from the query
        tool_agent = TransactionAgent(
            system_prompt=config.tool_agent_prompt,
            llm=llm,
            tool_agent_fields=fields,
        )
        extracted = tool_agent.extract_params(params.get("query", user_query))

        # Safety check: if ALL extracted params are null, ask for clarification
        # instead of returning all transactions unfiltered
        has_any_filter = any(
            v is not None and v != "" and v != "null"
            for v in extracted.values()
        )
        if not has_any_filter:
            print("[AgentEngine] No filters extracted — asking for clarification.")
            
            # Dynamically build question from fields
            field_labels = [f.get("label", f.get("name", "")) for f in fields]
            if field_labels:
                fields_desc = "transaction amount, date, and " + ", ".join(field_labels).lower()
            else:
                fields_desc = "transaction amount and date"
                
            answer = f"Could you please provide the {fields_desc}?"
        elif config.tool_data_source == "external" and config.external_db_connection:
            # Query user's external database
            rows = query_external_db(
                connection_string=config.external_db_connection,
                table_name=config.external_db_table,
                column_mappings=config.external_db_columns or {},
                extracted_params=extracted,
                tool_agent_fields=fields,
            )
            answer = format_external_results(rows, config.external_db_columns or {}, fields)
        else:
            # Query internal transactions table
            transactions = await crud.query_transactions(
                db=db,
                project_id=project_id,
                extracted_params=extracted,
                tool_agent_fields=fields,
            )
            answer = tool_agent.format_results(transactions)

        # Optionally apply formatter
        if config.enable_formatter:
            agent_path.append("formatter")
            formatter = DataFormatterAgent(system_prompt=config.formatter_prompt, llm=llm)
            answer = formatter.format_response(answer, "Format the transaction details clearly.")

    elif target == "direct_response":
        agent_path.append("direct_response")
        answer = params.get("message", "I am not sure how to respond.")

    else:
        answer = "I encountered an error processing your request."

    # 6. Calculate latency
    latency = round(time.time() - start_time, 3)

    # 7. Log query
    await crud.create_query_log(
        db=db,
        project_id=project_id,
        query=user_query,
        final_answer=answer,
        agent_path=agent_path,
        used_rag=used_rag,
        latency=latency,
        retrieved_chunks=retrieved_chunks,
    )

    print("-" * 80)
    print(f"[{project_id}] 🛤️  AGENT PATH: {' -> '.join(agent_path)}")
    print(f"[{project_id}] ✅ FINAL ANSWER: {answer}")
    print("=" * 80 + "\n")

    return {
        "answer": answer,
        "used_rag": used_rag,
        "agent_path": agent_path,
        "latency": latency,
        "retrieved_chunks": retrieved_chunks,
    }


def _error_response(message: str, start_time: float) -> dict:
    """Helper for error responses."""
    return {
        "answer": message,
        "used_rag": False,
        "agent_path": ["error"],
        "latency": round(time.time() - start_time, 3),
        "retrieved_chunks": [],
    }
