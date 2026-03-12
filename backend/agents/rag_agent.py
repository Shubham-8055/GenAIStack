"""
RAG Agent — Config-driven retrieval agent.
Accepts collection_name per project for namespace isolation.
Returns structured data (contexts + scores) for the debug panel.
"""
import os
from typing import List, Dict, Any

# Try to import Vector Stores
CHROMA_AVAILABLE = False
try:
    import chromadb
    from langchain_chroma import Chroma
    CHROMA_AVAILABLE = True
except ImportError:
    pass
except Exception:
    pass

from langchain_community.embeddings import HuggingFaceEmbeddings


# --- CONFIGURATION (from env) ---
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data_files", "chroma_db"
))
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")


class RAGAgent:
    def __init__(self, collection_name: str = "langchain", top_k: int = 4):
        """
        Args:
            collection_name: ChromaDB collection name (project-specific namespace).
            top_k: Number of chunks to retrieve.
        """
        self.collection_name = collection_name
        self.top_k = top_k
        self.vectorstore = None
        self._is_initialized = False
        self.use_mock = False

    def _lazy_init(self):
        if self._is_initialized:
            return

        print(f"[RAG Agent] Loading embeddings '{EMBEDDING_MODEL_NAME}' for collection '{self.collection_name}'...")

        # Authenticate if token is present
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            try:
                from huggingface_hub import login
                login(token=hf_token)
            except Exception as e:
                print(f"[RAG Agent] HF login warning: {e}")

        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu", "trust_remote_code": True},
            )

            if CHROMA_AVAILABLE:
                print(f"[RAG Agent] Connecting to ChromaDB at '{CHROMA_DB_PATH}'...")
                try:
                    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                    self.vectorstore = Chroma(
                        client=client,
                        embedding_function=self.embeddings,
                        collection_name=self.collection_name,
                    )
                    print(f"[RAG Agent] ChromaDB collection '{self.collection_name}' ready.")
                    self._is_initialized = True
                    return
                except Exception as e:
                    print(f"[RAG Agent] ChromaDB error: {e}")

            print("[RAG Agent] No vector store available — MOCK mode.")
            self.use_mock = True
            self._is_initialized = True

        except Exception as e:
            print(f"[RAG Agent] Critical init error: {e} — MOCK mode.")
            self.use_mock = True
            self._is_initialized = True

    def execute(self, query: str) -> Dict[str, Any]:
        """
        Search the vector store and return structured results.
        
        Returns:
            dict with keys:
                - context_text: str (joined context for synthesis)
                - chunks: list of {source, content, score}
        """
        self._lazy_init()

        if self.use_mock:
            return {
                "context_text": "No vector store available. Please upload documents first.",
                "chunks": [],
            }

        if not self.vectorstore:
            return {
                "context_text": "RAG Agent is offline.",
                "chunks": [],
            }

        try:
            if isinstance(query, dict):
                query = query.get("query", str(query))
            if not isinstance(query, str):
                query = str(query)

            print(f"[RAG Agent] Searching: '{query}' (top_k={self.top_k})")
            results = self.vectorstore.similarity_search_with_score(query, k=self.top_k)

            chunks = []
            contexts = []
            for doc, score in results:
                source = doc.metadata.get("source_path", "Unknown").split("/")[-1]
                content = doc.page_content.strip()
                chunks.append({"source": source, "content": content, "score": round(float(score), 4)})
                contexts.append(f"Source: {source}\nContent: {content}")
                print(f"   > Score: {score:.4f} | Source: {source}")

            context_text = "\n\n---\n\n".join(contexts) if contexts else "No relevant documents found."
            print(f"[RAG Agent] Returning {len(chunks)} chunks.")

            return {"context_text": context_text, "chunks": chunks}

        except Exception as e:
            print(f"[RAG Agent] Search error: {e}")
            return {"context_text": f"Error retrieving data: {e}", "chunks": []}
