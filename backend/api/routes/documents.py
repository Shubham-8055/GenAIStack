"""
Document upload and management routes.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.db import crud
from backend.services.ingestion import ingest_document, delete_document_vectors
from backend.models.schemas import DocumentResponse

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document, chunk it, embed it, and store in the project's vector store.
    Supported formats: PDF, TXT, MD.
    """
    # Verify project exists
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Validate file type
    allowed_extensions = (".pdf", ".txt", ".md")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        content = await file.read()

        # Read project's chunking config
        config = await crud.get_agent_config(db, project_id)
        chunk_size = config.chunk_size if config else None
        chunk_overlap = config.chunk_overlap if config else None

        doc_id, chunk_count = await ingest_document(
            db=db,
            project_id=project_id,
            filename=file.filename,
            file_content=content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Fetch the updated document record
        docs = await crud.get_documents(db, project_id)
        doc = next((d for d in docs if d.id == doc_id), None)
        if not doc:
            raise HTTPException(status_code=500, detail="Document created but not found.")
        return doc

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Documents API] Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all documents for a project."""
    return await crud.get_documents(db, project_id)


@router.delete("/{document_id}")
async def delete_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its vectors from the project's collection."""
    # Delete vectors from ChromaDB
    await delete_document_vectors(project_id, document_id)

    # Delete DB record
    deleted = await crud.delete_document(db, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {"status": "deleted", "document_id": str(document_id)}
