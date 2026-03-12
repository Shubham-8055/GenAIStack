"""
Chat playground route — runs the full agent pipeline.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.db import crud
from backend.core.agent_engine import run_pipeline
from backend.models.schemas import ChatRequest, ChatResponse, QueryLogResponse

router = APIRouter(prefix="/projects/{project_id}", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    project_id: uuid.UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the full agent pipeline for a project.
    Returns structured response with answer, agent path, latency, and retrieved chunks.
    """
    # Verify project exists
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
        result = await run_pipeline(
            db=db,
            project_id=project_id,
            user_query=body.message,
            chat_history=body.history,
        )
        return ChatResponse(**result)
    except Exception as e:
        print(f"[Chat API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=list[QueryLogResponse])
async def get_query_logs(
    project_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get recent query logs for a project."""
    logs = await crud.get_query_logs(db, project_id, limit=limit)
    return logs
