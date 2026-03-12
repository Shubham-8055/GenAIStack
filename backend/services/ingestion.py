"""
Document Ingestion Service.
Handles: file upload → chunk → embed → store in ChromaDB per-project.
"""
import os
import uuid
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import crud

# ChromaDB + LangChain imports
try:
    import chromadb
    from langchain_chroma import Chroma
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader


# --- Configuration from env ---
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data_files", "chroma_db"
))
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data_files", "uploads"
))

# Chunking defaults
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))


def _get_embeddings():
    """Get the embedding model (singleton-like via module-level caching)."""
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        try:
            from huggingface_hub import login
            login(token=hf_token)
        except Exception:
            pass

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu", "trust_remote_code": True},
    )


def _get_chroma_collection(collection_name: str):
    """Get or create a ChromaDB collection via LangChain wrapper."""
    if not CHROMA_AVAILABLE:
        raise RuntimeError("ChromaDB is not installed.")

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    embeddings = _get_embeddings()

    return Chroma(
        client=client,
        embedding_function=embeddings,
        collection_name=collection_name,
    )


async def ingest_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    filename: str,
    file_content: bytes,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> Tuple[uuid.UUID, int]:
    """
    Ingest a document into the project's vector store.
    
    Args:
        db: Database session.
        project_id: Project UUID.
        filename: Original filename.
        file_content: Raw file bytes.
        chunk_size: Override chunk size (defaults to env CHUNK_SIZE).
        chunk_overlap: Override chunk overlap (defaults to env CHUNK_OVERLAP).
    
    Returns:
        Tuple of (document_id, chunk_count).
    """
    # Use provided values or fall back to env defaults
    _chunk_size = chunk_size or CHUNK_SIZE
    _chunk_overlap = chunk_overlap or CHUNK_OVERLAP

    # 1. Create document record
    doc_record = await crud.create_document(db, project_id, filename)

    try:
        # 2. Save file to disk temporarily
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, f"{doc_record.id}_{filename}")
        with open(file_path, "wb") as f:
            f.write(file_content)

        # 3. Load and chunk
        if filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif filename.lower().endswith((".txt", ".md")):
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            # Try as text
            loader = TextLoader(file_path, encoding="utf-8")

        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
            length_function=len,
        )
        chunks = splitter.split_documents(documents)

        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "project_id": str(project_id),
                "document_id": str(doc_record.id),
                "filename": filename,
                "chunk_index": i,
            })

        # 4. Embed and store in project-specific collection
        collection_name = f"project_{project_id}"
        vectorstore = _get_chroma_collection(collection_name)
        vectorstore.add_documents(chunks)

        chunk_count = len(chunks)
        print(f"[Ingestion] Stored {chunk_count} chunks in collection '{collection_name}'.")

        # 5. Update document status
        await crud.update_document_status(db, doc_record.id, "ready", chunk_count)

        return doc_record.id, chunk_count

    except Exception as e:
        print(f"[Ingestion] Error: {e}")
        await crud.update_document_status(db, doc_record.id, "error", 0)
        raise


async def delete_document_vectors(project_id: uuid.UUID, document_id: uuid.UUID):
    """Delete all vectors for a specific document from the project's collection."""
    try:
        if not CHROMA_AVAILABLE:
            return

        collection_name = f"project_{project_id}"
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        try:
            collection = client.get_collection(collection_name)
            # Delete by metadata filter
            collection.delete(where={"document_id": str(document_id)})
            print(f"[Ingestion] Deleted vectors for document {document_id}.")
        except Exception as e:
            print(f"[Ingestion] Warning deleting vectors: {e}")

    except Exception as e:
        print(f"[Ingestion] Error deleting vectors: {e}")
