"""
Pydantic schemas for API request/response validation.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any

from pydantic import BaseModel, Field


# ─── Project Schemas ───

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectList(BaseModel):
    projects: List[ProjectResponse]
    total: int


# ─── Agent Config Schemas ───

class AgentConfigUpdate(BaseModel):
    guardrail_prompt: Optional[str] = None
    orchestrator_prompt: Optional[str] = None
    rag_prompt: Optional[str] = None
    formatter_prompt: Optional[str] = None
    enable_guardrail: Optional[bool] = None
    enable_rag: Optional[bool] = None
    enable_formatter: Optional[bool] = None
    enable_tool_agent: Optional[bool] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    tool_agent_prompt: Optional[str] = None
    tool_agent_fields: Optional[List[dict]] = None
    tool_data_source: Optional[str] = None
    external_db_connection: Optional[str] = None
    external_db_table: Optional[str] = None
    external_db_columns: Optional[dict] = None


class AgentConfigResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    guardrail_prompt: str
    orchestrator_prompt: str
    rag_prompt: str
    formatter_prompt: str
    enable_guardrail: bool
    enable_rag: bool
    enable_formatter: bool
    enable_tool_agent: bool
    tool_agent_prompt: str
    tool_agent_fields: List[dict]
    tool_data_source: str
    external_db_connection: str
    external_db_table: str
    external_db_columns: dict
    model_name: str
    temperature: float
    top_k: int
    chunk_size: int
    chunk_overlap: int

    model_config = {"from_attributes": True}


# ─── Document Schemas ───

class DocumentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Transaction Schemas ───

class TransactionResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    txn_date: datetime
    amount: float
    aadhaar_last4: str
    status: str
    txn_type: str
    bank_name: str
    rrn: str
    remarks: str
    custom_fields: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Chat Schemas ───

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = "default"
    history: List[dict] = []


class RetrievedChunk(BaseModel):
    source: str = ""
    content: str = ""
    score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    used_rag: bool = False
    agent_path: List[str] = []
    latency: float = 0.0
    retrieved_chunks: List[RetrievedChunk] = []


# ─── Query Log Schemas ───

class QueryLogResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    query: str
    final_answer: str
    agent_path: List[str]
    used_rag: bool
    latency: float
    retrieved_chunks: List[Any]
    created_at: datetime

    model_config = {"from_attributes": True}
