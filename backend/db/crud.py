"""
CRUD operations for all database models.
All functions are async and expect an AsyncSession.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.database import Project, AgentConfig, Document, QueryLog, Transaction


# ─── Projects ───

async def create_project(db: AsyncSession, name: str, description: str = "") -> Project:
    """Create a new project with default agent config."""
    project = Project(name=name, description=description)
    db.add(project)
    await db.flush()  # Get the project.id

    # Create default agent config
    config = AgentConfig(
        project_id=project.id,
        guardrail_prompt=get_default_guardrail_prompt(),
        orchestrator_prompt=get_default_orchestrator_prompt(),
        rag_prompt=get_default_rag_prompt(),
        formatter_prompt=get_default_formatter_prompt(),
        enable_guardrail=True,
        enable_rag=True,
        enable_formatter=True,
        enable_tool_agent=False,
        model_name="/model",
        temperature=0.0,
        top_k=4,
        chunk_size=1000,
        chunk_overlap=200,
        tool_agent_prompt=get_default_tool_agent_prompt(),
        tool_agent_fields=get_default_tool_agent_fields(),
    )
    db.add(config)
    await db.commit()
    await db.refresh(project)
    return project


async def get_projects(db: AsyncSession) -> List[Project]:
    """List all projects."""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[Project]:
    """Get a single project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """Delete a project and all related data (cascade)."""
    project = await get_project(db, project_id)
    if not project:
        return False
    await db.delete(project)
    await db.commit()
    return True


# ─── Agent Configs ───

async def get_agent_config(db: AsyncSession, project_id: uuid.UUID) -> Optional[AgentConfig]:
    """Get agent config for a project."""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def update_agent_config(db: AsyncSession, project_id: uuid.UUID, updates: dict) -> Optional[AgentConfig]:
    """Update agent config fields for a project."""
    config = await get_agent_config(db, project_id)
    if not config:
        return None

    for key, value in updates.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config


# ─── Documents ───

async def create_document(db: AsyncSession, project_id: uuid.UUID, filename: str) -> Document:
    """Create a document record (initially in 'processing' status)."""
    doc = Document(project_id=project_id, filename=filename, status="processing")
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def update_document_status(db: AsyncSession, doc_id: uuid.UUID, status: str, chunk_count: int = 0) -> Optional[Document]:
    """Update document status after ingestion."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc:
        doc.status = status
        doc.chunk_count = chunk_count
        await db.commit()
        await db.refresh(doc)
    return doc


async def get_documents(db: AsyncSession, project_id: uuid.UUID) -> List[Document]:
    """List all documents for a project."""
    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, doc_id: uuid.UUID) -> bool:
    """Delete a document record."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return False
    await db.delete(doc)
    await db.commit()
    return True


# ─── Query Logs ───

async def create_query_log(
    db: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    final_answer: str,
    agent_path: list,
    used_rag: bool,
    latency: float,
    retrieved_chunks: list = None,
) -> QueryLog:
    """Log a query and its result."""
    log = QueryLog(
        project_id=project_id,
        query=query,
        final_answer=final_answer,
        agent_path=agent_path,
        used_rag=used_rag,
        latency=latency,
        retrieved_chunks=retrieved_chunks or [],
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_query_logs(db: AsyncSession, project_id: uuid.UUID, limit: int = 50) -> List[QueryLog]:
    """Get recent query logs for a project."""
    result = await db.execute(
        select(QueryLog)
        .where(QueryLog.project_id == project_id)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ─── Default Prompts ───

def get_default_guardrail_prompt() -> str:
    return """You are the Finance Assistant Safety Guardrail.
Your ONLY job is to classify user queries as 'allowed' or 'blocked'.

### RULES FOR CLASSIFICATION:
1. **BLOCKED**:
   - Requests for Emergency Services (Police, Ambulance, Fire Brigade).
   - General Knowledge irrelevant to Banking/Finance (e.g., "Who is the Prime Minister?", "How to cook?", "Movie recommendations").
   - Hate speech, sexual content, or illegal activities.
   - **Criticism (Excessive)**: Simple complaints are allowed, but abusive rants should be blocked.

2. **ALLOWED**:
   - **Banking Products**: Cards, Loans, Accounts, Deposits, Insurance, Government Schemes.
   - **Operations**: Account closure, KYC, Nominee updates, Blocking cards, Limits.
   - **Transaction Queries**: Status checks, failure reasons (if related to banking).
   - **General Finance**: UPI, NEFT, IMPS, RTGS, Interest rates.
   - **Greetings/Small Talk**: Hi, Hello, Thanks, Bye.
   - **Partial/Broken Inputs**: Single keywords if relevant (e.g., "loan", "interest", "modify nominee").

### OUTPUT FORMAT:
You must output a JSON object.

If ALLOWED:
```json
{
  "status": "allowed"
}
```

If BLOCKED:
```json
{
  "status": "blocked",
  "topic": "The specific category of the violation.",
  "message": "A polite, single-sentence refusal explaining why you cannot answer."
}
```"""


def get_default_orchestrator_prompt() -> str:
    return """You are the Finance Orchestrator.

Your job is ONLY to decide which worker should handle the user's request.
You must NOT answer the question yourself unless it is a greeting or simple acknowledgement.

### WORKERS AVAILABLE:

1. `rag_agent`
Use this when the question requires:
- Banking product details (Savings account, Credit cards, Loans, Deposits)
- Account operations (KYC, reactivation, form filling, procedures, steps)
- Fees, eligibility, limits, charges
- Documents required
- Banking processes or guidelines
- Comparisons between products or services
- Any question that requires searching the knowledge base

Inputs:
- `query`: The search term for the database.
- `formatting_instruction`: Always include a formatting instruction.

2. `direct_response`
Use this ONLY for:
- Greetings: "hi", "hello", "good morning"
- Polite responses: "thanks", "ok", "got it"
- Simple confirmations: "yes", "no", "okay"
- Very general finance concepts that do NOT require bank-specific data

Inputs:
- `message`: The natural language response.

### STRICT DECISION RULES:
1. If the question needs bank-specific information → ALWAYS use `rag_agent`.
2. If the question is about procedures, steps, or documents → ALWAYS use `rag_agent`.
3. If the question is educational and generic → use `direct_response`.
4. When in doubt → choose `rag_agent`.

### OUTPUT FORMAT
Return ONLY valid JSON.

Example:
{
    "thought": "User is asking about account reactivation which requires knowledge base lookup.",
    "target": "rag_agent",
    "parameters": {
        "query": "How to reactivate dormant account",
        "formatting_instruction": "Format the answer clearly using headings and bullet points for steps."
    }
}

OR

{
    "thought": "User asked a greeting.",
    "target": "direct_response",
    "parameters": {
        "message": "Hello! How can I help you with finance or banking today?"
    }
}
"""


def get_default_rag_prompt() -> str:
    return """You are a professional Finance Assistant.
Your goal is to provide a helpful, conversational, and direct answer to the user's question based on the context.

Guidelines:
1. Start with a friendly, conversational 1-2 sentence opening.
2. Then, use the provided context to answer the question clearly.
3. If the context is missing information, politely say so.
4. End your answer with a short, engaging closing line to encourage further interaction."""


def get_default_formatter_prompt() -> str:
    return """You are a Data Formatter.
Your task is to take raw text/data and format it into a clear, structured presentation.

RULES:
1. **Tables**: If the data contains comparison or lists with attributes, use Markdown tables.
2. **Bullets**: Use bullet points for steps, features, or lists.
3. **Clarity**: Ensure the output is easy to read.
4. **No Logic Change**: Do NOT change the facts or meaning. Only change the presentation.
5. **JSON/Code**: If asked for JSON, output valid JSON.
6. **Preserve Intro**: Keep any conversational opening sentence as normal text at the top.

INPUT: Raw text from a retrieval system.
OUTPUT: Formatted Markdown (preserving conversational elements)."""


def get_default_tool_agent_prompt() -> str:
    return """You are a Transaction Parameter Extractor. You work as part of a tool-call agent pipeline.

When a user asks about a transaction, payment, or transfer, your ONLY job is to extract lookup parameters from their query.

### PARAMETERS TO EXTRACT:

1. `date` — The date of the transaction in **YYYY-MM-DD** format.
   - "today" → use current date
   - "yesterday" → use yesterday's date
   - "last week" → use the date 7 days ago
   - "1st March" → "2026-03-01"
   - If no date is mentioned → set to null

2. `amount` — The transaction amount as a **number** (no currency symbols).
   - "₹5000" → 5000
   - "five thousand" → 5000
   - "10k" → 10000
   - If no amount mentioned → set to null

3. `aadhaar_last4` — Last 4 digits of the Aadhaar number.
   - "Aadhaar ending 1234" → "1234"
   - "aadhaar 5678" → "5678"
   - If not mentioned → set to null

### RULES:
- Return ONLY valid JSON, nothing else.
- Do NOT answer the user's question.
- Do NOT add explanations or commentary.
- Even if only 1 parameter is found, still return all 3 fields.

### OUTPUT FORMAT:
```json
{
    "date": "2026-03-01",
    "amount": 5000,
    "aadhaar_last4": "1234"
}
```

### EXAMPLES:

Query: "Check my ₹5000 transaction done today, Aadhaar 1234"
→ {"date": "2026-03-02", "amount": 5000, "aadhaar_last4": "1234"}

Query: "Show status of payment of 2000 rupees"
→ {"date": null, "amount": 2000, "aadhaar_last4": null}

Query: "Transaction for Aadhaar ending 5678 yesterday"
→ {"date": "2026-03-01", "amount": null, "aadhaar_last4": "5678"}
"""


# ─── Transactions ───

async def query_transactions(
    db: AsyncSession,
    project_id: uuid.UUID,
    extracted_params: dict = None,
    tool_agent_fields: list = None,
) -> List[Transaction]:
    """Query transactions with dynamic filters."""
    from datetime import datetime, timedelta
    from sqlalchemy import cast, String

    extracted_params = extracted_params or {}
    tool_agent_fields = tool_agent_fields or []

    stmt = select(Transaction).where(Transaction.project_id == project_id)

    # Always filter by amount and date if provided
    amount = extracted_params.get("amount")
    txn_date = extracted_params.get("date")

    if amount is not None:
        stmt = stmt.where(Transaction.amount == amount)
    if txn_date:
        try:
            dt = datetime.fromisoformat(txn_date)
            stmt = stmt.where(
                Transaction.txn_date >= dt - timedelta(days=1),
                Transaction.txn_date <= dt + timedelta(days=1),
            )
        except ValueError:
            pass

    # Filter by dynamic custom fields
    for field in tool_agent_fields:
        field_name = field.get("name", "")
        field_value = extracted_params.get(field_name)
        if field_value:
            # For backward compat: aadhaar_last4 has a dedicated column
            if field_name == "aadhaar_last4":
                stmt = stmt.where(Transaction.aadhaar_last4 == str(field_value))
            else:
                # Filter on JSON custom_fields column
                stmt = stmt.where(
                    cast(Transaction.custom_fields[field_name].as_string(), String) == str(field_value)
                )

    stmt = stmt.order_by(Transaction.txn_date.desc()).limit(10)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_transactions(db: AsyncSession, project_id: uuid.UUID) -> List[Transaction]:
    """Get all transactions for a project."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.project_id == project_id)
        .order_by(Transaction.txn_date.desc())
    )
    return list(result.scalars().all())


async def seed_sample_transactions(
    db: AsyncSession,
    project_id: uuid.UUID,
    tool_agent_fields: list = None,
) -> int:
    """Seed sample transactions with dynamic custom fields."""
    from datetime import datetime, timedelta, timezone
    import random

    tool_agent_fields = tool_agent_fields or get_default_tool_agent_fields()

    banks = ["SBI", "HDFC", "ICICI", "PNB", "BOB", "Axis Bank"]
    statuses = ["success", "success", "success", "failed", "pending"]
    types = ["debit", "credit"]

    now = datetime.now(timezone.utc)
    txns = []
    for i in range(20):
        # Build custom_fields from configured fields
        custom = {}
        aadhaar_val = ""
        for field in tool_agent_fields:
            samples = field.get("sample_values", ["sample1", "sample2", "sample3"])
            value = random.choice(samples)
            custom[field["name"]] = value
            # Backward compat: also set aadhaar_last4 column
            if field["name"] == "aadhaar_last4":
                aadhaar_val = value

        txn = Transaction(
            project_id=project_id,
            txn_date=now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23)),
            amount=round(random.choice([500, 1000, 2000, 5000, 10000, 1500, 3000, 7500]), 2),
            aadhaar_last4=aadhaar_val,
            status=random.choice(statuses),
            txn_type=random.choice(types),
            bank_name=random.choice(banks),
            rrn=f"{random.randint(100000000000, 999999999999)}",
            remarks=random.choice([
                "AEPS cash withdrawal",
                "AEPS balance enquiry",
                "AEPS mini statement",
                "AEPS fund transfer",
                "AEPS cash deposit",
            ]),
            custom_fields=custom,
        )
        txns.append(txn)

    db.add_all(txns)
    await db.commit()
    return len(txns)


def get_default_tool_agent_fields() -> list:
    """Default lookup fields for the tool agent."""
    return [
        {
            "name": "aadhaar_last4",
            "label": "Aadhaar Last 4 Digits",
            "sample_values": ["1234", "5678", "9012", "3456", "7890"]
        }
    ]
