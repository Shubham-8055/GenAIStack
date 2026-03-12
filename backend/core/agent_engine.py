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
        tool_agent_section = """

3. `transaction_agent`
Use this when the user query involves:
- Checking a transaction status
- Looking up a specific payment or transfer
- Finding transaction details using date, amount, or Aadhaar number
- Any query mentioning "transaction", "payment status", "transfer", "RRN", or "Aadhaar"

Inputs:
- `query`: The original user query (the agent will extract params itself).

Example:
{
    "thought": "User is asking about a specific transaction status.",
    "target": "transaction_agent",
    "parameters": {
        "query": "Check status of 5000 transaction done yesterday, Aadhaar ending 1234"
    }
}
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
                "If the question is about checking a SPECIFIC transaction → ALWAYS use `transaction_agent`.\n5. When in doubt"
            )
        else:
            # Fallback: just append to the end
            orchestrator_prompt += tool_agent_section

    orchestrator = MainOrchestrator(
        system_prompt=orchestrator_prompt,
        rag_prompt=config.rag_prompt,
        llm=llm,
    )
    command = orchestrator.execute(user_query, chat_history)
    target = command.get("target", "error")
    params = command.get("parameters", {})

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

        # Route to internal or external DB
        if config.tool_data_source == "external" and config.external_db_connection:
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
