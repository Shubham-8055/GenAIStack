"""
Agent Configuration routes.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.db import crud
from backend.models.schemas import AgentConfigResponse, AgentConfigUpdate

router = APIRouter(prefix="/projects/{project_id}/config", tags=["agent-config"])


@router.get("", response_model=AgentConfigResponse)
async def get_agent_config(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get agent configuration for a project."""
    config = await crud.get_agent_config(db, project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found for this project.")
    return config


@router.put("", response_model=AgentConfigResponse)
async def update_agent_config(
    project_id: uuid.UUID,
    body: AgentConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update agent configuration for a project. Only provided fields are updated."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    config = await crud.update_agent_config(db, project_id, updates)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found for this project.")
    return config
