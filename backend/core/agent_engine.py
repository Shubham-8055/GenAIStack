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
from backend.agents.formatter_agent import DataFormatterAgent
from backend.agents.sql_tool_agent import SQLToolAgent
from backend.core.orchestrator import MainOrchestrator


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
        tool_agent_section = """

3. `transaction_agent`
Use this ONLY when the user asks about SQL database records, transactions, account status, or any external data. 
Even if the query is vague, route it to `transaction_agent` so the SQL agent can query the database or ask the user a clarifying question based on its findings.

Example:
```json
{
    "thought": "User is asking about a transaction, I will route to transaction_agent.",
    "target": "transaction_agent",
    "parameters": {
        "query": "Check my transactions"
    }
}
```
"""
        # Insert before the STRICT DECISION RULES section
        if "### STRICT DECISION RULES" in orchestrator_prompt:
            orchestrator_prompt = orchestrator_prompt.replace(
                "### STRICT DECISION RULES",
                tool_agent_section + "\n### STRICT DECISION RULES"
            )
            # Add transaction rule
            orchestrator_prompt = orchestrator_prompt.replace(
                "When in doubt",
                "If the question relates to ANY transactions, records, or specific account data → use `transaction_agent`.\nWhen in doubt"
            )
        else:
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
        agent_path.append("sql_tool_agent")

        # Get the external database URI
        db_uri = config.external_db_connection
        if config.tool_data_source != "external" or not db_uri:
            # Provide sensible fallback if no external DB is found
            answer = "External SQL database connection is not configured or activated. Please configure it in your Agent Settings."
        else:
            # Run the SQL agent
            sql_agent = SQLToolAgent(
                system_prompt=config.tool_agent_prompt,
                llm=llm,
                db_uri=db_uri,
            )
            
            query = params.get("query", user_query)
            answer = sql_agent.execute(user_query=query, chat_history=chat_history)

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

    # Strip any leaked <think> blocks from the final answer
    import re
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
    
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
