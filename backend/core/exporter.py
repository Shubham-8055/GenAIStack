"""
Project Exporter — Generates a standalone, ready-to-run chatbot project as a ZIP.
Takes the user's configured prompts, model settings, custom fields, documents,
and transaction data, and packages them into a self-contained project.
"""
import io
import csv
import json
import zipfile
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db import crud
from backend.models.database import Transaction, Document


async def export_project(db: AsyncSession, project_id: uuid.UUID) -> io.BytesIO:
    """Generate a standalone project ZIP file."""

    project = await crud.get_project(db, project_id)
    config = await crud.get_agent_config(db, project_id)

    if not project or not config:
        raise ValueError("Project or config not found")

    project_name = project.name.lower().replace(" ", "_")

    # Get transactions
    result = await db.execute(
        select(Transaction)
        .where(Transaction.project_id == project_id)
        .order_by(Transaction.txn_date.desc())
    )
    transactions = list(result.scalars().all())

    # Get documents
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
    )
    documents = list(result.scalars().all())

    # Build config dict
    cfg = {
        "project_name": project.name,
        "description": project.description or "",
        "guardrail_prompt": config.guardrail_prompt,
        "orchestrator_prompt": config.orchestrator_prompt,
        "rag_prompt": config.rag_prompt,
        "formatter_prompt": config.formatter_prompt,
        "tool_agent_prompt": config.tool_agent_prompt,
        "enable_guardrail": config.enable_guardrail,
        "enable_rag": config.enable_rag,
        "enable_formatter": config.enable_formatter,
        "enable_tool_agent": config.enable_tool_agent,
        "tool_agent_fields": config.tool_agent_fields or [],
        "tool_data_source": config.tool_data_source or "internal",
        "external_db_connection": config.external_db_connection or "",
        "external_db_table": config.external_db_table or "",
        "external_db_columns": config.external_db_columns or {},
        "model_name": config.model_name,
        "temperature": config.temperature,
        "top_k": config.top_k,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
    }

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        root = f"{project_name}_chatbot"

        # 1. config.json
        zf.writestr(f"{root}/config.json", json.dumps(cfg, indent=2, ensure_ascii=False))

        # 2. Transaction data as CSV
        if transactions:
            csv_buf = io.StringIO()
            custom_field_names = [f["name"] for f in (config.tool_agent_fields or [])]
            fieldnames = ["txn_date", "amount", "aadhaar_last4", "status", "txn_type",
                          "bank_name", "rrn", "remarks"] + custom_field_names
            writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
            writer.writeheader()
            for txn in transactions:
                row = {
                    "txn_date": txn.txn_date.isoformat() if txn.txn_date else "",
                    "amount": str(txn.amount),
                    "aadhaar_last4": txn.aadhaar_last4 or "",
                    "status": txn.status or "",
                    "txn_type": txn.txn_type or "",
                    "bank_name": txn.bank_name or "",
                    "rrn": txn.rrn or "",
                    "remarks": txn.remarks or "",
                }
                custom = txn.custom_fields or {}
                for fn in custom_field_names:
                    row[fn] = custom.get(fn, "")
                writer.writerow(row)
            zf.writestr(f"{root}/data/transactions.csv", csv_buf.getvalue())

        # 3. Document references (actual files would need disk access)
        if documents:
            doc_list = []
            for doc in documents:
                doc_list.append({
                    "filename": doc.filename,
                    "chunk_count": doc.chunk_count,
                    "status": doc.status,
                })
            zf.writestr(f"{root}/data/documents.json", json.dumps(doc_list, indent=2))

        # 4. Main app — standalone FastAPI with hardcoded config
        zf.writestr(f"{root}/app.py", _gen_app_py(cfg))

        # 5. Agents
        zf.writestr(f"{root}/agents/__init__.py", "")
        zf.writestr(f"{root}/agents/guardrails_agent.py", _gen_guardrails_agent())
        zf.writestr(f"{root}/agents/rag_agent.py", _gen_rag_agent())
        zf.writestr(f"{root}/agents/formatter_agent.py", _gen_formatter_agent())
        zf.writestr(f"{root}/agents/sql_tool_agent.py", _gen_sql_tool_agent())

        # 6. Core
        zf.writestr(f"{root}/core/__init__.py", "")
        zf.writestr(f"{root}/core/orchestrator.py", _gen_orchestrator())
        zf.writestr(f"{root}/core/pipeline.py", _gen_pipeline(cfg))

        # 7. Docker
        zf.writestr(f"{root}/Dockerfile", _gen_dockerfile())
        zf.writestr(f"{root}/docker-compose.yml", _gen_docker_compose(cfg))
        zf.writestr(f"{root}/requirements.txt", _gen_requirements(cfg))
        zf.writestr(f"{root}/.env.example", _gen_env_example())

        # 8. README
        zf.writestr(f"{root}/README.md", _gen_readme(cfg, project.name))

    zip_buffer.seek(0)
    return zip_buffer


# ─── File Generators ────────────────────────────────────────────

def _gen_app_py(cfg: dict) -> str:
    return '''"""
Standalone Chatbot API — Generated by GenAI Platform.
Run: uvicorn app:app --host 0.0.0.0 --port 8000
"""
import json
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Load config
with open("config.json") as f:
    CONFIG = json.load(f)

app = FastAPI(title=CONFIG["project_name"] + " Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    used_rag: bool = False
    agent_path: list = []
    latency: float = 0.0


@app.get("/health")
def health():
    return {"status": "ok", "project": CONFIG["project_name"]}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process a chat message through the configured pipeline."""
    from core.pipeline import run_pipeline

    result = run_pipeline(
        user_query=req.message,
        chat_history=req.history,
        config=CONFIG,
    )
    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
'''


def _gen_pipeline(cfg: dict) -> str:
    """Generate the standalone pipeline that uses hardcoded config."""
    tool_agent_block = ""
    if cfg["enable_tool_agent"]:
        if cfg["tool_data_source"] == "external":
            tool_agent_block = '''
    elif target == "transaction_agent" or target == "sql_tool_agent":
        agent_path.append("sql_tool_agent")
        from agents.sql_tool_agent import SQLToolAgent
        sql_agent = SQLToolAgent(
            system_prompt=config["tool_agent_prompt"],
            llm=llm,
            db_uri=config["external_db_connection"],
        )
        answer = sql_agent.execute(user_query=user_query, chat_history=chat_history)
'''
        else:
            tool_agent_block = '''
    elif target == "transaction_agent" or target == "sql_tool_agent":
        agent_path.append("csv_fallback")
        answer = "Data source is not external DB. This export only supports SQLAgent via External DB right now."
'''

    formatter_tool = ""
    if cfg["enable_tool_agent"] and cfg["enable_formatter"]:
        formatter_tool = '''
        if config.get("enable_formatter"):
            agent_path.append("formatter")
            from agents.formatter_agent import DataFormatterAgent
            fmt = DataFormatterAgent(system_prompt=config["formatter_prompt"], llm=llm)
            answer = fmt.format_response(answer, "Format the transaction details clearly.")
'''

    return f'''"""
Pipeline — Runs the full agent chain with hardcoded config.
"""
import time
import json
import os
from langchain_openai import ChatOpenAI


def get_llm(config: dict):
    """Create LLM instance from config."""
    # Use environment model name if defined, else fallback to project model name
    env_model = os.getenv("LLM_MODEL_NAME")
    model = env_model or config.get("model_name", "google/gemma-4-31b-it:free")
    if env_model and (config.get("model_name") == "google/gemma-4-31b-it:free" or config.get("model_name") == "/model"):
        model = env_model

    return ChatOpenAI(
        openai_api_base=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        openai_api_key=os.getenv("LLM_API_KEY", ""),
        model_name=model,
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
            return {{"answer": rejection, "used_rag": False,
                     "agent_path": ["guardrails"], "latency": round(time.time() - start_time, 3)}}

    # 2. Orchestrator routing
    agent_path.append("orchestrator")

    # Dynamic tool agent injection
    orchestrator_prompt = config["orchestrator_prompt"]
    if config.get("enable_tool_agent"):
        tool_section = """
3. `transaction_agent`
Use this when the user query involves checking a transaction status,
looking up a payment/transfer, or finding transaction details by date, amount, or ID.
Inputs: {{"query": "the original user query"}}
"""
        if "### STRICT DECISION RULES" in orchestrator_prompt:
            orchestrator_prompt = orchestrator_prompt.replace(
                "### STRICT DECISION RULES",
                tool_section + "\\n### STRICT DECISION RULES"
            )

    from core.orchestrator import MainOrchestrator
    orchestrator = MainOrchestrator(
        system_prompt=orchestrator_prompt,
        rag_prompt=config["rag_prompt"],
        llm=llm,
    )
    command = orchestrator.execute(user_query, chat_history)
    target = command.get("target", "error")
    params = command.get("parameters", {{}})

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
{tool_agent_block}{formatter_tool}
    elif target == "direct_response":
        agent_path.append("direct_response")
        answer = params.get("message", "I am not sure how to respond.")
    else:
        answer = "I encountered an error processing your request."

    latency = round(time.time() - start_time, 3)
    return {{"answer": answer, "used_rag": used_rag, "agent_path": agent_path, "latency": latency}}


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

    lines = ["Found **" + str(len(rows)) + "** matching transaction(s):\\n"]
    for i, row in enumerate(rows, 1):
        status = row.get("status", "unknown").lower()
        emoji = {{"success": "✅", "failed": "❌", "pending": "⏳"}}.get(status, "❓")
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
        lines.append("### Transaction " + str(i) + "\\n| Field | Details |\\n|---|---|\\n" + "\\n".join(table_rows) + "\\n")
    return "\\n".join(lines)
'''


def _gen_orchestrator() -> str:
    return '''"""
Orchestrator — Routes user queries to the appropriate agent.
"""
import json
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class MainOrchestrator:
    def __init__(self, system_prompt: str, rag_prompt: str, llm):
        self.llm = llm
        self.system_prompt = system_prompt
        self.rag_prompt = rag_prompt

    def route_request(self, messages: list) -> dict:
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"[Orchestrator] Error: {e}")
            return {"target": "error", "message": str(e)}

    def execute(self, user_query: str, chat_history: list = None) -> dict:
        chat_history = chat_history or []
        messages = [SystemMessage(content=self.system_prompt)]
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_query))
        command = self.route_request(messages)
        print(f"[Orchestrator] Route: {command.get('target')}")
        return command

    def synthesize_answer(self, query: str, context: str) -> str:
        messages = [
            SystemMessage(content=self.rag_prompt),
            HumanMessage(content=f"Context:\\n{context}\\n\\nUser Question: {query}"),
        ]
        return self.llm.invoke(messages).content
'''


def _gen_guardrails_agent() -> str:
    return '''"""Guardrails Agent — Validates user queries for safety."""
import json
from langchain_core.messages import SystemMessage, HumanMessage


class GuardrailsAgent:
    def __init__(self, system_prompt: str, llm):
        self.llm = llm
        self.system_prompt = system_prompt

    def check(self, user_query: str) -> tuple:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_query),
        ]
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content.strip())
            is_safe = result.get("is_safe", True)
            message = result.get("message", "")
            return is_safe, message
        except Exception:
            return True, ""
'''


def _gen_rag_agent() -> str:
    return '''"""
RAG Agent — Retrieves context from ChromaDB and returns relevant chunks.
Requires chromadb and sentence-transformers.
"""
import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


class RAGAgent:
    def __init__(self, collection_name: str = "documents", top_k: int = 4):
        self.top_k = top_k
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = int(os.getenv("CHROMA_PORT", "8001"))

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            client_settings=None,
        )

    def execute(self, query: str) -> dict:
        try:
            results = self.vectorstore.similarity_search(query, k=self.top_k)
            chunks = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
            context_text = "\\n\\n---\\n\\n".join([doc.page_content for doc in results])
            return {"context_text": context_text, "chunks": chunks}
        except Exception as e:
            print(f"[RAG] Error: {e}")
            return {"context_text": "", "chunks": []}
'''


def _gen_formatter_agent() -> str:
    return '''"""Formatter Agent — Formats responses according to instructions."""
from langchain_core.messages import SystemMessage, HumanMessage


class DataFormatterAgent:
    def __init__(self, system_prompt: str, llm):
        self.llm = llm
        self.system_prompt = system_prompt

    def format_response(self, raw_answer: str, instruction: str) -> str:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Formatting instruction: {instruction}\\n\\nContent to format:\\n{raw_answer}"),
        ]
        try:
            return self.llm.invoke(messages).content
        except Exception:
            return raw_answer
'''


def _gen_sql_tool_agent() -> str:
    return '''"""SQL Tool Agent — Integrates with LangChain SQLDatabaseToolkit."""
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase

class SQLToolAgent:
    def __init__(self, system_prompt: str, llm, db_uri: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.db_uri = db_uri
        
        sync_uri = db_uri.replace("+asyncpg", "") if db_uri else ""
        
        try:
            if sync_uri:
                self.db = SQLDatabase.from_uri(sync_uri)
                self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
                
                self.agent_executor = create_sql_agent(
                    llm=self.llm,
                    toolkit=self.toolkit,
                    prefix=self.system_prompt,
                    verbose=True,
                    handle_parsing_errors=True
                )
            else:
                self.agent_executor = None
        except Exception as e:
            print(f"[SQLToolAgent] Init error: {e}")
            self.agent_executor = None

    def execute(self, user_query: str, chat_history: list = None) -> str:
        if not self.agent_executor:
            return "Error: Could not connect to the external database."
        try:
            context_query = user_query
            if chat_history:
                context_lines = [f"{msg.get('role', '')}: {msg.get('content', '')}" for msg in chat_history[-4:]]
                if context_lines:
                    history_str = "\\n".join(context_lines)
                    context_query = f"Recent Chat History:\\n{history_str}\\n\\nCurrent User Request: {user_query}"
            
            response = self.agent_executor.invoke({"input": context_query})
            return response.get("output", "I could not find the information.")
        except Exception as e:
            return f"An error occurred while querying the database: {str(e)}"
'''


def _gen_dockerfile() -> str:
    return '''FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
'''


def _gen_docker_compose(cfg: dict) -> str:
    return f'''version: "3.8"

services:
  chatbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LLM_BASE_URL=${{LLM_BASE_URL:-http://host.docker.internal:8080/v1}}
      - LLM_API_KEY=${{LLM_API_KEY:-not-needed}}
    volumes:
      - .:/app
    restart: unless-stopped
'''


def _gen_requirements(cfg: dict) -> str:
    reqs = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "langchain",
        "langchain-openai",
        "langchain-community",
    ]
    if cfg.get("enable_rag"):
        reqs.extend(["langchain-chroma", "chromadb", "sentence-transformers"])
    if cfg.get("tool_data_source") == "external":
        reqs.extend(["sqlalchemy", "psycopg2-binary"])
    return "\n".join(reqs) + "\n"


def _gen_env_example() -> str:
    return '''# LLM Configuration
LLM_BASE_URL=http://localhost:8080/v1
LLM_API_KEY=not-needed

# ChromaDB (if using RAG)
CHROMA_HOST=localhost
CHROMA_PORT=8001
'''


def _gen_readme(cfg: dict, project_name: str) -> str:
    agents = []
    if cfg["enable_guardrail"]:
        agents.append("✅ Guardrails Agent")
    agents.append("✅ Orchestrator (Router)")
    if cfg["enable_rag"]:
        agents.append("✅ RAG Agent (Knowledge Base)")
    if cfg["enable_tool_agent"]:
        agents.append("✅ Tool Agent (Transaction Lookup)")
    if cfg["enable_formatter"]:
        agents.append("✅ Formatter Agent")
    agents_str = "\n".join(f"- {a}" for a in agents)

    fields_str = ""
    for f in cfg.get("tool_agent_fields", []):
        fields_str += f"\n- **{f.get('label', f['name'])}** (`{f['name']}`)"

    return f'''# {project_name} — AI Chatbot

Generated by **GenAI Platform** on {datetime.now().strftime("%d %b %Y, %I:%M %p")}.

## Agents Configured
{agents_str}

## Quick Start

### Option 1: Docker (Recommended)
```bash
cp .env.example .env
# Edit .env with your LLM endpoint
docker compose up --build
```

### Option 2: Local Python
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your LLM endpoint
python app.py
```

### Chat API
```bash
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "Hello!"}}'
```

## Configuration

All agent prompts and settings are in `config.json`. You can edit them to customize behavior.

### Model Settings
- **Model**: `{cfg["model_name"]}`
- **Temperature**: `{cfg["temperature"]}`
- **Top K**: `{cfg["top_k"]}`

{f"### Custom Lookup Fields{fields_str}" if fields_str else ""}

### Data Source
- **Type**: `{cfg["tool_data_source"]}`
{f"- **External DB**: `{cfg['external_db_table']}`" if cfg["tool_data_source"] == "external" else "- Transaction data is in `data/transactions.csv`"}

## Project Structure
```
├── app.py                  # FastAPI entry point
├── config.json             # All prompts & settings
├── core/
│   ├── orchestrator.py     # Query router
│   └── pipeline.py         # Full agent pipeline
├── agents/
│   ├── guardrails_agent.py
│   ├── rag_agent.py
│   ├── formatter_agent.py
│   └── transaction_agent.py
├── data/
│   └── transactions.csv    # Transaction data
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
'''
