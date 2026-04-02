# GenAI Platform

A modular, config-driven, multi-project GenAI platform for building and deploying AI chatbots with RAG (Retrieval-Augmented Generation).

**Create projects → upload documents → configure agents via UI → chat with your data → inspect every step.**

---

## Architecture

```mermaid
graph TD;
    User[User Message] --> Guardrails;
    Guardrails -->|Allowed| Orchestrator;
    Orchestrator -->|Domain Knowledge/FAQ| RAG_Agent;
    Orchestrator -->|General Chat / Clarification| direct_response;
    Orchestrator -->|Live Transaction Data| SQL_Tool_Agent(Transaction Agent);
    RAG_Agent --> Formatter;
    SQL_Tool_Agent --> Formatter;
    Formatter --> Response[User Reply];
    direct_response --> Response;
```

---

## Features

- **Multi-Project** — isolated projects with their own documents, prompts, and vector store
- **Config-Driven Agents** — enable/disable guardrails, RAG, formatter via UI toggles
- **Editable Prompts** — modify all agent prompts from the UI (no code changes needed)
- **Document Ingestion** — upload PDF/TXT/MD files, auto-chunk, embed, and store per-project
- **Chat Playground** — test your agent pipeline with a debug panel (agent path, latency, retrieved chunks)
- **Query Logs** — searchable/filterable history of every query with full trace
- **LLM Abstraction** — swap models by changing one env variable

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | FastAPI (async) + Pydantic |
| Database | PostgreSQL 16 (projects, configs, logs) |
| Vector Store | ChromaDB (per-project collections) |
| LLM | OpenAI-compatible API (configurable) |
| Deployment | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js 18+](https://nodejs.org/) (for local frontend dev)
- An OpenAI-compatible LLM endpoint (or use the default)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/genai-platform.git
cd genai-platform
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Required — your LLM endpoint
LLM_BASE_URL=http://your-llm-server:port/v1
LLM_API_KEY=your-api-key
LLM_MODEL_NAME=/model

# Optional — for gated HuggingFace models
HF_TOKEN=hf_your_token_here
```

### 3. Start everything with Docker

```bash
docker compose up --build
```

This starts:
| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Redis Commander | http://localhost:8081 |

### 4. Start the frontend (dev mode)

```bash
cd frontend
npm install
npm run dev
```

Frontend will be at **http://localhost:5173**

### 5. Use the platform

1. **Create a project** from the Dashboard
2. Go to **Agent Settings** to customize prompts or toggle agents
3. Go to **Documents** to upload your knowledge base files (PDF, TXT, MD)
4. Go to **Playground** to chat — the debug panel shows everything happening behind the scenes
5. Go to **Query Logs** to inspect every past query

---

## Project Structure

```
├── backend/
│   ├── api/routes/          # REST endpoints (projects, config, chat, docs, logs)
│   ├── agents/              # Guardrails, RAG, Formatter agents
│   ├── core/                # Agent engine (pipeline runner), orchestrator
│   ├── db/                  # SQLAlchemy models, CRUD, DB init
│   ├── models/              # Pydantic schemas + ORM models
│   ├── services/            # LLM provider, document ingestion
│   ├── main.py              # FastAPI app factory
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Settings, Documents, Playground, Logs
│   │   ├── components/      # Layout, chat components
│   │   ├── services/        # API client
│   │   └── context/         # Playground state persistence
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects` | List projects |
| `GET` | `/api/v1/projects/{id}` | Get project |
| `DELETE` | `/api/v1/projects/{id}` | Delete project |
| `GET` | `/api/v1/projects/{id}/config` | Get agent config |
| `PUT` | `/api/v1/projects/{id}/config` | Update agent config |
| `POST` | `/api/v1/projects/{id}/chat` | Chat (runs full pipeline) |
| `GET` | `/api/v1/projects/{id}/logs` | Query logs |
| `POST` | `/api/v1/projects/{id}/documents/upload` | Upload document |
| `GET` | `/api/v1/projects/{id}/documents` | List documents |
| `DELETE` | `/api/v1/projects/{id}/documents/{doc_id}` | Delete document |

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@postgres:5432/genai_platform` |
| `LLM_BASE_URL` | OpenAI-compatible API base URL | `http://183.82.7.228:9532/v1` |
| `LLM_API_KEY` | API key for LLM | `EMPTY` |
| `LLM_MODEL_NAME` | Model path/name | `/model` |
| `HF_TOKEN` | HuggingFace token (optional) | — |
| `EMBEDDING_MODEL_NAME` | Sentence-transformers model | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHROMA_DB_PATH` | ChromaDB storage path | `/app/data_files/chroma_db` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173,http://localhost:3000` |

## Production Deployment

For production, build the frontend and serve via Docker:

```bash
# Build and run everything
docker compose up --build -d

# View logs
docker compose logs -f backend
```

The frontend Dockerfile builds and serves via Nginx at port 3000.

---

## License

MIT
