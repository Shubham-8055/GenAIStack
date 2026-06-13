# GenAI Platform — Modular Multi-Agent Chatbot Builder

A production-ready, config-driven GenAI platform designed to build, customize, and deploy isolated, context-aware AI chatbots with RAG (Retrieval-Augmented Generation) and dynamic SQL querying capabilities.

**Create isolated projects → Upload domain knowledge → Configure agent prompts via UI → Interact in Playground → Trace execution latency & path.**

---

## 📸 Platform Walkthrough

### 1. Project Dashboard
The central control center to manage isolated project environments. Each project maintains its own configuration settings, uploaded vector store indexes, and logs.
![Project Dashboard](screenshots/dashboard.png)

### 2. Multi-Agent Configuration Portal
Fine-tune guardrail prompts, orchestrator routing rules, synthesis settings, and output formatting guidelines. Enables dynamic toggling of agent steps.

* **System & Guardrails Prompts Configuration**:
  ![Agent Settings 1](screenshots/agent_setting_1.png)
* **Orchestrator Routing Configuration**:
  ![Agent Settings 2](screenshots/agent_setting_2.png)
* **Agent Output Prompts & Parameter Settings**:
  ![Agent Settings 3](screenshots/agent_setting_3.png)

### 3. Document Upload & Knowledge Base
Upload documents (TXT, PDF, MD) to build a semantic vector database partitioned per project.
![Document Upload](screenshots/documents.png)

### 4. Playground & Debugging Trace
Test chatbot pipelines in real-time. The playground features an execution tracing panel that visualizes the routing path, model latency, and retrieved chunks.
![Playground Trace](screenshots/chat_playground.png)

### 5. Transaction History & Usage Audits
Audit individual agent execution steps, system transactions, and database operations with cost tracking metrics.
![Transaction History](screenshots/transactions.png)

### 6. Observability & Query Logs
A history portal displaying execution stats, routing outcomes, token latencies, and detailed agent steps for performance audits and debugging.
![Query Logs](screenshots/logs.png)

---

## 🏗️ System Architecture & Data Flow

The platform employs a modular multi-agent pipeline where queries are filtered, classified, routed, and formatted before returning to the user:

```mermaid
graph TD;
    User[User Message] --> Guardrails[Guardrails Agent];
    Guardrails -->|Allowed| Orchestrator[Orchestrator Router];
    Guardrails -->|Blocked| Rejection[Safety Rejection Response];
    
    Orchestrator -->|FAQ / Knowledge Base| RAG_Agent[RAG Retrieval Agent];
    Orchestrator -->|General / Conversational| direct_response[Direct LLM Reply];
    Orchestrator -->|Relational Lookup / Transaction Data| SQL_Agent[SQL Tool Agent];
    
    RAG_Agent --> Formatter[Formatter Agent];
    SQL_Agent --> Formatter;
    
    Formatter --> Response[Final Formatted Response];
    direct_response --> Response;
```

### Pipeline Sequence Breakdown
1. **Safety Guardrail**: Standardizes safety checks. Classifies the query as `allowed` or `blocked` based on custom guidelines.
2. **Orchestrator (Router)**: Parses user intent and routes queries to either the **RAG Agent**, **SQL Database Agent**, or generates a **Direct Response**.
3. **Execution Nodes**:
   - **RAG Agent**: Queries project-specific vector indexes in ChromaDB using sentence embeddings.
   - **SQL Agent**: Connects securely to dynamic database columns to extract specific account records.
4. **Output Formatter**: Ensures consistent response structure (e.g. rendering text/tables in clean Markdown).

---

## 💡 Key Design & Engineering Highlights

This codebase is structured around several modern software engineering principles and architectural patterns:

### 1. Abstracted LLM Service Layer
- Implemented in [llm_provider.py](file:///F:/Study%20Material/projects/GenAIStack/backend/services/llm_provider.py), this class centralizes ChatOpenAI instantiations. 
- Allows switching between **OpenAI**, **OpenRouter**, **Ollama**, or custom **vLLM** endpoints by editing a single environment variable, without refactoring agent files.
- Integrates a smart override system: Database default placeholders are dynamically bypassed in favor of local `.env` setups.

### 2. Standalone Code Generator (Exporter Core)
- Configured in [exporter.py](file:///F:/Study%20Material/projects/GenAIStack/backend/core/exporter.py), the platform compiles settings, files, database connections, and prompts into a standalone, ready-to-run FastAPI microservice.
- Generates a zip folder structure containing clean Docker configurations, requirements lists, and pipeline agents.

### 3. Isolated Vector Spaces
- Implemented on top of **ChromaDB**, documents are partitioned into separate collections per project ID to prevent any data leak or cross-talk between chatbot databases.

---

## 🛠️ Technology Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | React 19 + Vite + Tailwind CSS | Modern SPA UI with modular, responsive layout. |
| **Backend API**| FastAPI (Async Python 3.9) | High-performance asynchronous REST endpoints. |
| **Relational DB**| PostgreSQL 16 + SQLAlchemy | Stores project configurations, agent prompts, and logs. |
| **Vector DB** | ChromaDB | Local vector store database for semantic embedding search. |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Lightweight embedding model running on CPU. |
| **Cache & Queue**| Redis + Redis Commander | High-speed cache for playground transactions. |
| **Containerization**| Docker & Docker Compose | Containerized system service orchestration. |

---

## ⚙️ Configuration (.env)

The platform is configured entirely via environment variables. Create a `.env` file in the root folder based on `.env.example`:

```env
# Relational Database Connection
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/genai_platform

# LLM Configuration (OpenAI, OpenRouter, Ollama, etc.)
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL_NAME=gpt-4o-mini

# Hugging Face Settings (for gated embedding models)
HF_TOKEN=

# ChromaDB & Document Upload Storage
CHROMA_DB_PATH=/app/data_files/chroma_db
UPLOAD_DIR=/app/data_files/uploads
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# Cache Server
REDIS_HOST=redis
REDIS_PORT=6379

# Cross-Origin Policies (CORS)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 🚀 Quick Start Setup

### Step 1: Run Services with Docker Compose
From the root directory:
```bash
# Clone the repository
git clone https://github.com/Shubham-8055/GenAIStack.git
cd GenAIStack

# Copy example configurations
cp .env.example .env

# Build and launch all backend services
docker compose up --build -d
```

### Step 2: Start local React Web App
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 🛣️ API Observability Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service health status |
| `POST` | `/api/v1/projects` | Initialize a new chatbot environment |
| `GET` | `/api/v1/projects/{id}/config` | Fetch agent triggers and prompt templates |
| `PUT` | `/api/v1/projects/{id}/config` | Update active chatbot config settings |
| `POST` | `/api/v1/projects/{id}/chat` | Process queries through the execution pipeline |
| `GET` | `/api/v1/projects/{id}/logs` | Trace latencies, logs, and routing paths |
