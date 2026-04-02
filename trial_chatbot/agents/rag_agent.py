"""
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
            context_text = "\n\n---\n\n".join([doc.page_content for doc in results])
            return {"context_text": context_text, "chunks": chunks}
        except Exception as e:
            print(f"[RAG] Error: {e}")
            return {"context_text": "", "chunks": []}
