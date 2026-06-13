"""
Pipeline Exporter — Generates a standalone, runnable Python project
from a user's agent pipeline configuration.

The exported ZIP is a self-contained project the user can open in any
editor, install deps, and run immediately. It includes:
  - Their specific agent prompts hardcoded
  - Agent classes (guardrail, orchestrator, RAG, formatter)
  - Pipeline runner
  - LLM provider
  - Document ingestion script
  - Their uploaded knowledge-base files
  - CLI + API entry points
  - requirements.txt, .env.example, README
"""
import io
import json
import os
import re
import zipfile


UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/data_files/uploads")


def generate_pipeline_zip(project, config, documents) -> io.BytesIO:
    """Generate a standalone pipeline project as an in-memory ZIP."""
    buf = io.BytesIO()
    safe = re.sub(r'[^\w\-]', '_', project.name)
    root = f"{safe}/"

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ── Agent files ──
        zf.writestr(root + "agents/__init__.py", "")
        zf.writestr(root + "agents/guardrail.py", _guardrail_code(config.guardrail_prompt))
        zf.writestr(root + "agents/orchestrator.py", _orchestrator_code(config.orchestrator_prompt))
        zf.writestr(root + "agents/rag_agent.py", _rag_agent_code(config.rag_prompt))
        zf.writestr(root + "agents/formatter.py", _formatter_code(config.formatter_prompt))

        # ── Core ──
        zf.writestr(root + "pipeline.py", _pipeline_code(config))
        zf.writestr(root + "llm_provider.py", _llm_provider_code(config.model_name))
        zf.writestr(root + "ingest.py", _ingest_code(config))
        zf.writestr(root + "main.py", _main_code(safe))
        zf.writestr(root + "app.py", _api_code(safe))

        # ── Frontend ──
        zf.writestr(root + "static/index.html", _chatbot_html(project.name))

        # ── Config reference ──
        config_json = {
            "project_name": project.name,
            "description": project.description,
            "agents": {
                "guardrail": {"enabled": config.enable_guardrail},
                "rag": {"enabled": config.enable_rag, "top_k": config.top_k},
                "formatter": {"enabled": config.enable_formatter},
            },
            "model": {
                "name": config.model_name,
                "temperature": config.temperature,
            },
            "chunking": {
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
            }
        }
        zf.writestr(root + "config.json", json.dumps(config_json, indent=2))

        # ── Knowledge base docs ──
        for doc in documents:
            file_path = os.path.join(UPLOAD_DIR, f"{doc.id}_{doc.filename}")
            if os.path.exists(file_path):
                zf.write(file_path, root + f"knowledge_base/{doc.filename}")

        # ── Support files ──
        zf.writestr(root + "requirements.txt", _requirements())
        zf.writestr(root + ".env.example", _env_example())
        zf.writestr(root + "README.md", _readme(project.name, config, documents))

    buf.seek(0)
    return buf, safe


# ═══════════════════════════════════════════════════════════════════
# CODE GENERATORS — each returns a complete, runnable Python file
# ═══════════════════════════════════════════════════════════════════

def _esc(prompt: str) -> str:
    """Escape a prompt for embedding in triple-quoted strings."""
    return prompt.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def _guardrail_code(prompt: str) -> str:
    return f'''"""
Guardrail Agent — Classifies user queries as allowed or blocked.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage

SYSTEM_PROMPT = """{_esc(prompt)}"""


class GuardrailAgent:
    def __init__(self, llm):
        self.llm = llm

    def check(self, user_query: str, chat_history: list = None) -> dict:
        """Returns {{"status": "allowed"}} or {{"status": "blocked", "topic": "...", "message": "..."}}"""
        context = ""
        if chat_history:
            context = "\\n".join(
                f"{{m[\'role\'].upper()}}: {{m[\'content\']}}" for m in chat_history[-4:]
            )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\\n{{context}}\\n\\nUser Query: {{user_query}}"),
        ]

        try:
            resp = self.llm.invoke(messages)
            content = resp.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"[Guardrail] Error: {{e}} — defaulting to allowed")
            return {{"status": "allowed"}}
'''


def _orchestrator_code(prompt: str) -> str:
    return f'''"""
Orchestrator — Routes user queries to the appropriate agent.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

SYSTEM_PROMPT = """{_esc(prompt)}"""


class Orchestrator:
    def __init__(self, llm):
        self.llm = llm

    def route(self, user_query: str, chat_history: list = None) -> dict:
        """Returns routing decision: {{"target": "rag_agent"|"direct_response", "parameters": {{...}}}}"""
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in (chat_history or []):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_query))

        try:
            resp = self.llm.invoke(messages)
            content = resp.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"[Orchestrator] Error: {{e}}")
            return {{"target": "error", "message": str(e)}}
'''


def _rag_agent_code(rag_prompt: str) -> str:
    return f'''"""
RAG Agent — Retrieves relevant chunks from ChromaDB and synthesizes answers.
"""
import os
from langchain_core.messages import SystemMessage, HumanMessage

try:
    import chromadb
    from langchain_chroma import Chroma
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from langchain_community.embeddings import HuggingFaceEmbeddings

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "knowledge_base")

SYNTHESIS_PROMPT = """{_esc(rag_prompt)}"""


class RAGAgent:
    def __init__(self, top_k: int = 4):
        self.top_k = top_k
        self.vectorstore = None
        self._initialized = False

    def _init(self):
        if self._initialized:
            return
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={{"device": "cpu", "trust_remote_code": True}},
            )
            if CHROMA_AVAILABLE:
                client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                self.vectorstore = Chroma(
                    client=client,
                    embedding_function=self.embeddings,
                    collection_name=COLLECTION_NAME,
                )
                print(f"[RAG] Connected to collection '{{COLLECTION_NAME}}'")
        except Exception as e:
            print(f"[RAG] Init error: {{e}}")
        self._initialized = True

    def retrieve(self, query: str) -> dict:
        """Search vector store. Returns {{"context_text": str, "chunks": [...]}}"""
        self._init()
        if not self.vectorstore:
            return {{"context_text": "No vector store. Run: python ingest.py", "chunks": []}}

        try:
            results = self.vectorstore.similarity_search_with_score(query, k=self.top_k)
            chunks = []
            contexts = []
            for doc, score in results:
                source = doc.metadata.get("source", "Unknown").split("/")[-1]
                content = doc.page_content.strip()
                chunks.append({{"source": source, "content": content, "score": round(float(score), 4)}})
                contexts.append(f"Source: {{source}}\\nContent: {{content}}")
            context_text = "\\n\\n---\\n\\n".join(contexts) if contexts else "No relevant documents found."
            return {{"context_text": context_text, "chunks": chunks}}
        except Exception as e:
            return {{"context_text": f"Error: {{e}}", "chunks": []}}

    def synthesize(self, llm, query: str, context: str) -> str:
        """Generate a natural language answer from retrieved context."""
        messages = [
            SystemMessage(content=SYNTHESIS_PROMPT),
            HumanMessage(content=f"Context:\\n{{context}}\\n\\nUser Question: {{query}}"),
        ]
        return llm.invoke(messages).content
'''


def _formatter_code(prompt: str) -> str:
    return f'''"""
Formatter Agent — Formats raw text into structured, readable output.
"""
from langchain_core.messages import SystemMessage, HumanMessage

SYSTEM_PROMPT = """{_esc(prompt)}"""


class FormatterAgent:
    def __init__(self, llm):
        self.llm = llm

    def format(self, text: str, instruction: str = "format clearly") -> str:
        """Format the text according to the instruction."""
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"INSTRUCTION: {{instruction}}\\n\\nDATA:\\n{{text}}"),
            ]
            return self.llm.invoke(messages).content
        except Exception as e:
            print(f"[Formatter] Error: {{e}}")
            return text
'''


def _pipeline_code(config) -> str:
    return f'''"""
Pipeline — Runs the full agent pipeline.
  Guardrail → Orchestrator → RAG → Synthesizer → Formatter
"""
import time
from llm_provider import get_llm
from agents.guardrail import GuardrailAgent
from agents.orchestrator import Orchestrator
from agents.rag_agent import RAGAgent
from agents.formatter import FormatterAgent

# Pipeline configuration (from your project settings)
ENABLE_GUARDRAIL = {config.enable_guardrail}
ENABLE_RAG = {config.enable_rag}
ENABLE_FORMATTER = {config.enable_formatter}
TOP_K = {config.top_k}


def run(query: str, chat_history: list = None) -> dict:
    """
    Run the full agent pipeline on a user query.

    Returns:
        dict with: answer, agent_path, used_rag, latency, retrieved_chunks
    """
    start = time.time()
    chat_history = chat_history or []
    agent_path = []
    used_rag = False
    chunks = []

    llm = get_llm()

    # 1. Guardrail
    if ENABLE_GUARDRAIL:
        agent_path.append("guardrail")
        guard = GuardrailAgent(llm)
        result = guard.check(query, chat_history)
        if result.get("status") == "blocked":
            return {{
                "answer": result.get("message", "I cannot answer that."),
                "agent_path": agent_path,
                "used_rag": False,
                "latency": round(time.time() - start, 3),
                "retrieved_chunks": [],
            }}

    # 2. Orchestrator routing
    agent_path.append("orchestrator")
    orch = Orchestrator(llm)
    command = orch.route(query, chat_history)
    target = command.get("target", "error")
    params = command.get("parameters", {{}})

    # 3. Execute
    if target == "rag_agent" and ENABLE_RAG:
        agent_path.append("rag_agent")
        used_rag = True

        rag = RAGAgent(top_k=TOP_K)
        rag_result = rag.retrieve(params.get("query", query))
        context = rag_result["context_text"]
        chunks = rag_result["chunks"]

        # Synthesize
        agent_path.append("synthesizer")
        answer = rag.synthesize(llm, query, context)

        # Format
        fmt_instruction = params.get("formatting_instruction", "")
        if ENABLE_FORMATTER and fmt_instruction:
            agent_path.append("formatter")
            answer = FormatterAgent(llm).format(answer, fmt_instruction)

    elif target == "direct_response":
        agent_path.append("direct_response")
        answer = params.get("message", "I'm not sure how to respond.")
    else:
        answer = "Error processing your request."

    return {{
        "answer": answer,
        "agent_path": agent_path,
        "used_rag": used_rag,
        "latency": round(time.time() - start, 3),
        "retrieved_chunks": chunks,
    }}
'''


def _llm_provider_code(model_name: str) -> str:
    return f'''"""
LLM Provider — Centralizes LLM creation.
Configure via environment variables or .env file.
"""
import os
from langchain_openai import ChatOpenAI

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "{model_name}")


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Create an LLM instance."""
    return ChatOpenAI(
        model=LLM_MODEL_NAME,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=temperature,
    )
'''


def _ingest_code(config) -> str:
    chunk_size = getattr(config, 'chunk_size', 1000) or 1000
    chunk_overlap = getattr(config, 'chunk_overlap', 200) or 200
    return f'''"""
Document Ingestion — Chunks and embeds documents from knowledge_base/ into ChromaDB.
Run this once before using the pipeline:  python ingest.py
"""
import os
import sys

try:
    import chromadb
    from langchain_chroma import Chroma
except ImportError:
    print("Install ChromaDB: pip install chromadb langchain-chroma")
    sys.exit(1)

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "knowledge_base")
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")
CHUNK_SIZE = {chunk_size}
CHUNK_OVERLAP = {chunk_overlap}


def ingest():
    if not os.path.exists(KNOWLEDGE_DIR):
        print(f"No knowledge_base/ directory found at {{KNOWLEDGE_DIR}}")
        return

    files = [f for f in os.listdir(KNOWLEDGE_DIR) if not f.startswith(".")]
    if not files:
        print("No files found in knowledge_base/")
        return

    print(f"Embedding model: {{EMBEDDING_MODEL}}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={{"device": "cpu", "trust_remote_code": True}},
    )

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    vectorstore = Chroma(
        client=client,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )

    total_chunks = 0
    for filename in files:
        filepath = os.path.join(KNOWLEDGE_DIR, filename)
        print(f"Processing: {{filename}}...", end=" ")

        try:
            if filename.lower().endswith(".pdf"):
                loader = PyPDFLoader(filepath)
            else:
                loader = TextLoader(filepath, encoding="utf-8")

            docs = loader.load()
            chunks = splitter.split_documents(docs)

            for i, chunk in enumerate(chunks):
                chunk.metadata["source"] = filename
                chunk.metadata["chunk_index"] = i

            vectorstore.add_documents(chunks)
            total_chunks += len(chunks)
            print(f"{{len(chunks)}} chunks")

        except Exception as e:
            print(f"ERROR: {{e}}")

    print(f"\\nDone! {{total_chunks}} total chunks in collection '{{COLLECTION_NAME}}'")
    print(f"ChromaDB path: {{os.path.abspath(CHROMA_DB_PATH)}}")


if __name__ == "__main__":
    ingest()
'''


def _main_code(project_name: str) -> str:
    return f'''"""
{project_name} — CLI Chat Interface
Run:  python main.py
"""
import os
from dotenv import load_dotenv
load_dotenv()  # Load .env file

import pipeline


def main():
    print("=" * 60)
    print(f"  {project_name} Agent Pipeline")
    print("=" * 60)
    print("Type your questions below. Type 'quit' to exit.\\n")

    history = []

    while True:
        query = input("You: ").strip()
        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = pipeline.run(query, history)

        print(f"\\nBot: {{result['answer']}}")
        print(f"  [path: {{' → '.join(result['agent_path'])}} | "
              f"latency: {{result['latency']}}s | "
              f"RAG: {{result['used_rag']}}]\\n")

        history.append({{"role": "user", "content": query}})
        history.append({{"role": "assistant", "content": result["answer"]}})


if __name__ == "__main__":
    main()
'''


def _api_code(project_name: str) -> str:
    return f'''"""
{project_name} — API Server with Chat UI
Run:  uvicorn app:app --reload
Open:  http://localhost:8000
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import pipeline

app = FastAPI(title="{project_name}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve static files (chat UI)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.get("/")
async def index():
    """Serve the chat UI."""
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {{"message": "Chat UI not found. Use POST /chat for API access."}}


@app.post("/chat")
async def chat(req: ChatRequest):
    result = pipeline.run(req.message, req.history)
    return result


@app.get("/health")
async def health():
    return {{"status": "ok", "project": "{project_name}"}}
'''


def _requirements() -> str:
    return """# Core
langchain>=0.2.0
langchain-openai>=0.1.0
langchain-community>=0.2.0
langchain-chroma>=0.1.0

# Vector Store
chromadb>=0.4.0

# Embeddings
sentence-transformers>=2.2.0

# Document Loaders
pypdf>=3.9.0

# API (optional — for app.py)
fastapi>=0.100.0
uvicorn>=0.20.0

# Environment
python-dotenv>=1.0.0
"""


def _env_example() -> str:
    return """# ─── LLM Configuration ───
# Point this to your OpenAI-compatible endpoint (vLLM, Ollama, OpenAI, etc.)
LLM_BASE_URL=http://your-llm-server:port/v1
LLM_API_KEY=your-api-key
LLM_MODEL_NAME=/model

# ─── Embeddings ───
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# ─── ChromaDB ───
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION=knowledge_base
"""


def _readme(name: str, config, documents) -> str:
    doc_list = "\n".join(f"  - {d.filename}" for d in documents) if documents else "  (no documents included)"

    agents_enabled = []
    if config.enable_guardrail:
        agents_enabled.append("Guardrail")
    agents_enabled.append("Orchestrator")
    if config.enable_rag:
        agents_enabled.append("RAG Agent")
    if config.enable_formatter:
        agents_enabled.append("Formatter")

    pipeline_flow = " → ".join(agents_enabled)

    return f"""# {name}

A standalone agent pipeline exported from the GenAI Platform.

## Pipeline

```
{pipeline_flow}
```

**Model:** `{config.model_name}` | **Temperature:** `{config.temperature}` | **Top-K chunks:** `{config.top_k}`

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env — set your LLM_BASE_URL and LLM_API_KEY

# 3. Ingest your documents into ChromaDB
python ingest.py

# 4. Run the server & open the chat UI
uvicorn app:app --reload
# Open http://localhost:8000 in your browser

# OR run the CLI chat instead
python main.py
```

## Project Structure

```
{name}/
├── agents/
│   ├── guardrail.py       ← Safety classifier
│   ├── orchestrator.py    ← Query router
│   ├── rag_agent.py       ← Retrieval + synthesis
│   └── formatter.py       ← Output formatter
├── knowledge_base/        ← Your documents
{doc_list}
├── static/
│   └── index.html         ← Chat UI (opens at /)
├── pipeline.py            ← Full pipeline runner
├── llm_provider.py        ← LLM abstraction
├── ingest.py              ← Document ingestion script
├── main.py                ← CLI chat interface
├── app.py                 ← FastAPI server + UI
├── config.json            ← Pipeline config reference
├── requirements.txt
├── .env.example
└── README.md
```

## Chat UI

Start the server and open **http://localhost:8000** — a modern chatbot interface
with typing indicators, markdown rendering, and debug info (agent path, latency, RAG status).

## API Usage

```bash
# Start server
uvicorn app:app --reload

# Chat
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "What is UPI?"}}'
```

## Customization

- **Edit prompts**: Modify the `SYSTEM_PROMPT` in each agent file
- **Change model**: Update `LLM_MODEL_NAME` in `.env`
- **Add documents**: Drop files in `knowledge_base/` and re-run `python ingest.py`
- **Toggle agents**: Edit the flags in `pipeline.py` (`ENABLE_GUARDRAIL`, etc.)
"""


def _chatbot_html(project_name: str) -> str:
    """Generate a beautiful, self-contained chatbot HTML page."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project_name} — Chat</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    color: #e2e8f0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  /* Header */
  .header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 24px;
    background: rgba(15, 23, 42, 0.8);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    flex-shrink: 0;
  }}
  .header-left {{ display: flex; align-items: center; gap: 12px; }}
  .logo {{
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #f59e0b, #f97316);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 700; color: white;
  }}
  .header h1 {{ font-size: 16px; font-weight: 600; color: #f1f5f9; }}
  .header p {{ font-size: 11px; color: #64748b; margin-top: 2px; }}
  .header-actions {{ display: flex; gap: 8px; }}
  .header-actions button {{
    padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.15);
    background: rgba(30, 41, 59, 0.6); color: #94a3b8; font-size: 12px; cursor: pointer;
    transition: all 0.2s;
  }}
  .header-actions button:hover {{ background: rgba(30, 41, 59, 0.9); color: #e2e8f0; }}

  /* Chat container */
  .chat-wrapper {{ display: flex; flex: 1; overflow: hidden; }}

  .chat-main {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}

  .messages {{
    flex: 1; overflow-y: auto; padding: 24px;
    scroll-behavior: smooth;
  }}
  .messages::-webkit-scrollbar {{ width: 6px; }}
  .messages::-webkit-scrollbar-track {{ background: transparent; }}
  .messages::-webkit-scrollbar-thumb {{ background: rgba(148, 163, 184, 0.15); border-radius: 3px; }}

  .messages-inner {{ max-width: 800px; margin: 0 auto; }}

  /* Welcome */
  .welcome {{
    text-align: center; padding: 80px 24px;
  }}
  .welcome-icon {{
    width: 64px; height: 64px; border-radius: 16px; margin: 0 auto 16px;
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(249, 115, 22, 0.15));
    border: 1px solid rgba(245, 158, 11, 0.2);
    display: flex; align-items: center; justify-content: center;
    font-size: 28px;
  }}
  .welcome h2 {{ font-size: 22px; font-weight: 700; color: #f1f5f9; margin-bottom: 8px; }}
  .welcome p {{ color: #64748b; font-size: 14px; max-width: 400px; margin: 0 auto; line-height: 1.6; }}

  /* Messages */
  .msg {{ display: flex; margin-bottom: 16px; animation: fadeIn 0.3s ease; }}
  .msg-user {{ justify-content: flex-end; }}
  .msg-bot {{ justify-content: flex-start; }}

  .msg-bubble {{
    max-width: 75%; padding: 12px 16px; border-radius: 16px;
    font-size: 14px; line-height: 1.65; word-wrap: break-word;
  }}
  .msg-user .msg-bubble {{
    background: linear-gradient(135deg, #f59e0b, #f97316);
    color: white; border-bottom-right-radius: 4px;
  }}
  .msg-bot .msg-bubble {{
    background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(148, 163, 184, 0.1);
    color: #e2e8f0; border-bottom-left-radius: 4px;
  }}
  .msg-bot .msg-bubble p {{ margin: 0 0 8px; }}
  .msg-bot .msg-bubble p:last-child {{ margin-bottom: 0; }}
  .msg-bot .msg-bubble ul, .msg-bot .msg-bubble ol {{ padding-left: 20px; margin: 8px 0; }}
  .msg-bot .msg-bubble code {{
    background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; font-size: 13px;
  }}
  .msg-bot .msg-bubble pre {{
    background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px;
    overflow-x: auto; margin: 8px 0;
  }}
  .msg-bot .msg-bubble pre code {{ background: none; padding: 0; }}
  .msg-bot .msg-bubble strong {{ color: #fbbf24; }}

  /* Typing */
  .typing {{ display: flex; align-items: center; gap: 4px; padding: 12px 16px; }}
  .typing-dot {{
    width: 6px; height: 6px; background: #f59e0b; border-radius: 50%;
    animation: bounce 1.2s infinite;
  }}
  .typing-dot:nth-child(2) {{ animation-delay: 0.15s; }}
  .typing-dot:nth-child(3) {{ animation-delay: 0.3s; }}

  /* Input */
  .input-area {{
    padding: 16px 24px 20px;
    background: rgba(15, 23, 42, 0.8);
    backdrop-filter: blur(12px);
    border-top: 1px solid rgba(148, 163, 184, 0.08);
    flex-shrink: 0;
  }}
  .input-box {{
    max-width: 800px; margin: 0 auto;
    display: flex; align-items: center; gap: 8px;
    background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 14px; padding: 4px;
    transition: border-color 0.2s;
  }}
  .input-box:focus-within {{ border-color: rgba(245, 158, 11, 0.4); }}
  .input-box input {{
    flex: 1; background: none; border: none; outline: none; padding: 12px 16px;
    color: #e2e8f0; font-size: 14px; font-family: inherit;
  }}
  .input-box input::placeholder {{ color: #475569; }}
  .send-btn {{
    width: 40px; height: 40px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #f59e0b, #f97316);
    color: white; cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: all 0.2s; flex-shrink: 0;
  }}
  .send-btn:hover {{ transform: scale(1.05); }}
  .send-btn:disabled {{ opacity: 0; pointer-events: none; }}
  .send-btn svg {{ width: 18px; height: 18px; }}

  /* Debug panel */
  .debug-panel {{
    width: 300px; background: rgba(15, 23, 42, 0.95); border-left: 1px solid rgba(148, 163, 184, 0.1);
    overflow-y: auto; padding: 20px; flex-shrink: 0;
    transition: width 0.3s ease; display: flex; flex-direction: column;
  }}
  .debug-panel.collapsed {{ width: 0; padding: 0; overflow: hidden; border: none; }}
  .debug-title {{ font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px; }}
  .debug-section {{ margin-bottom: 16px; }}
  .debug-label {{ font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }}
  .debug-label .dot {{ width: 6px; height: 6px; border-radius: 50%; }}
  .debug-value {{ font-size: 13px; color: #e2e8f0; }}
  .debug-value.big {{ font-size: 20px; font-weight: 700; }}
  .agent-badge {{
    display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;
    background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); color: #a5b4fc;
    margin: 2px 4px 2px 0;
  }}
  .agent-arrow {{ color: #475569; font-size: 11px; margin: 0 2px; }}
  .rag-badge {{
    display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;
  }}
  .rag-yes {{ background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); color: #6ee7b7; }}
  .rag-no {{ background: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.15); color: #94a3b8; }}
  .chunk-card {{
    background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 8px; padding: 10px; margin-top: 6px; font-size: 12px; color: #94a3b8;
    line-height: 1.5; max-height: 80px; overflow: hidden;
  }}
  .debug-empty {{ text-align: center; padding: 40px 0; color: #475569; font-size: 13px; }}

  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  @keyframes bounce {{
    0%, 80%, 100% {{ transform: translateY(0); }}
    40% {{ transform: translateY(-8px); }}
  }}

  @media (max-width: 768px) {{
    .debug-panel {{ display: none !important; }}
    .msg-bubble {{ max-width: 88%; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <div class="header-left">
      <div class="logo">&#9889;</div>
      <div>
        <h1>{project_name}</h1>
        <p>Agent Pipeline Chat</p>
      </div>
    </div>
    <div class="header-actions">
      <button onclick="clearChat()">Clear</button>
      <button onclick="toggleDebug()">Debug</button>
    </div>
  </div>

  <div class="chat-wrapper">
    <div class="chat-main">
      <div class="messages" id="messages">
        <div class="messages-inner" id="messagesInner">
          <div class="welcome" id="welcome">
            <div class="welcome-icon">&#9889;</div>
            <h2>{project_name}</h2>
            <p>Your personal AI assistant. Ask anything about your knowledge base. Responses include debug info in the right panel.</p>
          </div>
        </div>
      </div>
      <div class="input-area">
        <div class="input-box">
          <input type="text" id="userInput" placeholder="Type a message..." autocomplete="off" />
          <button class="send-btn" id="sendBtn" onclick="sendMessage()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
      </div>
    </div>

    <div class="debug-panel" id="debugPanel">
      <div class="debug-title">Debug Info</div>
      <div id="debugContent">
        <div class="debug-empty">Send a message to see debug info.</div>
      </div>
    </div>
  </div>

<script>
  const API_URL = window.location.origin;
  let history = [];
  let debugOpen = true;

  const input = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const messagesEl = document.getElementById('messagesInner');
  const welcome = document.getElementById('welcome');
  const messagesContainer = document.getElementById('messages');

  input.addEventListener('keydown', e => {{ if (e.key === 'Enter' && !e.shiftKey) sendMessage(); }});

  function toggleDebug() {{
    debugOpen = !debugOpen;
    document.getElementById('debugPanel').classList.toggle('collapsed', !debugOpen);
  }}

  function clearChat() {{
    history = [];
    messagesEl.innerHTML = `<div class="welcome" id="welcome">
      <div class="welcome-icon">&#9889;</div>
      <h2>{project_name}</h2>
      <p>Your personal AI assistant. Ask anything about your knowledge base.</p>
    </div>`;
    document.getElementById('debugContent').innerHTML = '<div class="debug-empty">Send a message to see debug info.</div>';
  }}

  function addMessage(role, content) {{
    const w = document.getElementById('welcome');
    if (w) w.remove();

    const div = document.createElement('div');
    div.className = 'msg msg-' + (role === 'user' ? 'user' : 'bot');
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';

    if (role === 'user') {{
      bubble.textContent = content;
    }} else {{
      bubble.innerHTML = marked.parse(content);
    }}

    div.appendChild(bubble);
    messagesEl.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return div;
  }}

  function addTyping() {{
    const div = document.createElement('div');
    div.className = 'msg msg-bot';
    div.id = 'typing';
    div.innerHTML = '<div class="typing"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';
    messagesEl.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }}

  function removeTyping() {{
    const t = document.getElementById('typing');
    if (t) t.remove();
  }}

  function updateDebug(data) {{
    const debugEl = document.getElementById('debugContent');
    const path = (data.agent_path || []).map(a => `<span class="agent-badge">${{a}}</span>`).join('<span class="agent-arrow">→</span>');
    const ragClass = data.used_rag ? 'rag-yes' : 'rag-no';
    const ragText = data.used_rag ? 'Yes' : 'No';
    const chunks = data.retrieved_chunks || [];

    let chunksHtml = '';
    if (chunks.length > 0) {{
      chunksHtml = `<div class="debug-section">
        <div class="debug-label"><span class="dot" style="background:#fbbf24"></span>Retrieved Chunks (${{chunks.length}})</div>
        ${{chunks.map(c => `<div class="chunk-card">${{typeof c === 'string' ? c : (c.content || JSON.stringify(c)).substring(0, 150)}}...</div>`).join('')}}
      </div>`;
    }}

    debugEl.innerHTML = `
      <div class="debug-section">
        <div class="debug-label"><span class="dot" style="background:#818cf8"></span>Agent Path</div>
        <div class="debug-value">${{path}}</div>
      </div>
      <div class="debug-section">
        <div class="debug-label"><span class="dot" style="background:#34d399"></span>Latency</div>
        <div class="debug-value big">${{data.latency || 0}}s</div>
      </div>
      <div class="debug-section">
        <div class="debug-label"><span class="dot" style="background:#c084fc"></span>Used RAG</div>
        <div class="debug-value"><span class="rag-badge ${{ragClass}}">${{ragText}}</span></div>
      </div>
      ${{chunksHtml}}
    `;
  }}

  async function sendMessage() {{
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    sendBtn.disabled = true;
    addMessage('user', text);
    addTyping();

    try {{
      const res = await fetch(API_URL + '/chat', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ message: text, history: history }})
      }});
      const data = await res.json();
      removeTyping();

      addMessage('bot', data.answer || 'No response.');
      updateDebug(data);

      history.push({{ role: 'user', content: text }});
      history.push({{ role: 'assistant', content: data.answer }});
    }} catch (err) {{
      removeTyping();
      addMessage('bot', '⚠️ Error: Could not reach the server. Is the backend running?');
    }}

    sendBtn.disabled = false;
    input.focus();
  }}
</script>
</body>
</html>'''
