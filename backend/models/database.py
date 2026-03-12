"""
SQLAlchemy ORM models for the GenAI Platform.
Tables: projects, agent_configs, documents, query_logs, transactions
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, Float, Integer,
    DateTime, ForeignKey, JSON, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    agent_config = relationship("AgentConfig", back_populates="project", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="project", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(name='{self.name}')>"


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Prompts
    guardrail_prompt = Column(Text, default="")
    orchestrator_prompt = Column(Text, default="")
    rag_prompt = Column(Text, default="")
    formatter_prompt = Column(Text, default="")

    # Toggles
    enable_guardrail = Column(Boolean, default=True)
    enable_rag = Column(Boolean, default=True)
    enable_formatter = Column(Boolean, default=True)
    enable_tool_agent = Column(Boolean, default=False)

    # Tool Agent settings
    tool_agent_prompt = Column(Text, default="")
    tool_agent_fields = Column(JSON, default=list)  # [{name, label, sample_values}]
    tool_data_source = Column(String(50), default="internal")  # "internal" or "external"
    external_db_connection = Column(Text, default="")           # connection string
    external_db_table = Column(String(255), default="")        # table name
    external_db_columns = Column(JSON, default=dict)           # {date_col, amount_col, ...}

    # Model settings
    model_name = Column(String(255), default="/model")
    temperature = Column(Float, default=0.0)
    top_k = Column(Integer, default=4)

    # Chunking settings
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)

    # Relationship
    project = relationship("Project", back_populates="agent_config")

    def __repr__(self):
        return f"<AgentConfig(project_id='{self.project_id}')>"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="processing")  # processing, ready, error
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    project = relationship("Project", back_populates="documents")

    def __repr__(self):
        return f"<Document(filename='{self.filename}')>"


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    query = Column(Text, nullable=False)
    final_answer = Column(Text, default="")
    agent_path = Column(JSON, default=list)
    used_rag = Column(Boolean, default=False)
    latency = Column(Float, default=0.0)
    retrieved_chunks = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    project = relationship("Project", back_populates="query_logs")

    def __repr__(self):
        return f"<QueryLog(query='{self.query[:50]}...')>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    txn_date = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    aadhaar_last4 = Column(String(4), default="")         # kept for backward compat
    status = Column(String(50), default="pending")       # success, failed, pending
    txn_type = Column(String(50), default="debit")        # credit, debit
    bank_name = Column(String(255), default="")
    rrn = Column(String(50), default="")                  # retrieval reference number
    remarks = Column(Text, default="")
    custom_fields = Column(JSON, default=dict)            # dynamic user-defined fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    project = relationship("Project", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(amount={self.amount}, status='{self.status}')>"
