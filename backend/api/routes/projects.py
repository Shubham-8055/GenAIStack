"""
Project CRUD routes + Pipeline export/import.
"""
import io
import os
import uuid
import json
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.db import crud
from backend.models.schemas import ProjectCreate, ProjectResponse, ProjectList

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/data_files/uploads")

router = APIRouter(prefix="/projects", tags=["projects"])


# ─── Standard CRUD ───

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new project with default agent configuration."""
    try:
        project = await crud.create_project(db, name=body.name, description=body.description)
        return project
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Project '{body.name}' already exists.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ProjectList)
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    projects = await crud.get_projects(db)
    return ProjectList(projects=projects, total=len(projects))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single project by ID."""
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a project and all related data."""
    deleted = await crud.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"status": "deleted", "project_id": str(project_id)}


# ─── Pipeline Export (standalone project ZIP) ───

@router.get("/{project_id}/export")
async def export_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Export the project as a standalone, ready-to-run chatbot.

    The ZIP contains:
      - app.py (FastAPI chat endpoint)
      - config.json (all prompts, toggles, model settings)
      - agents/ (guardrail, rag, formatter, transaction agent)
      - core/ (orchestrator, pipeline)
      - data/ (transactions.csv)
      - Dockerfile, docker-compose.yml, requirements.txt
      - README.md with setup instructions
    """
    from backend.core.exporter import export_project as generate_zip

    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
        zip_buffer = await generate_zip(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    safe_name = project.name.lower().replace(" ", "_")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_chatbot.zip"'
        },
    )


# ─── Import ───

@router.post("/import", response_model=ProjectResponse, status_code=201)
async def import_project(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Import a project from a config JSON or ZIP bundle.
    Creates a new project with imported prompts, toggles, and model config.
    """
    raw = await file.read()
    filename = file.filename or ""

    if filename.endswith(".json"):
        try:
            data = json.loads(raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON file.")
        return await _create_from_config(db, data)

    # ZIP — extract config
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file. Upload a .zip or .json.")

    config_name = None
    for name in zf.namelist():
        basename = os.path.basename(name)
        if basename in ("config.json", "project_config.json"):
            config_name = name
            break

    if not config_name:
        raise HTTPException(status_code=400, detail="ZIP missing config — not a valid project export.")

    data = json.loads(zf.read(config_name))
    project = await _create_from_config(db, data)

    # Re-ingest documents if present
    from backend.services.ingestion import ingest_document

    doc_files = [
        n for n in zf.namelist()
        if ("knowledge_base/" in n or "documents/" in n) and not n.endswith("/")
    ]
    for doc_path in doc_files:
        doc_filename = os.path.basename(doc_path)
        doc_bytes = zf.read(doc_path)
        try:
            await ingest_document(db, project.id, doc_filename, doc_bytes)
        except Exception as e:
            print(f"[Import] Warning: failed to ingest '{doc_filename}': {e}")

    return project


async def _create_from_config(db: AsyncSession, data: dict):
    """Helper: create project + apply agent config from parsed export data."""
    proj_data = data.get("project", data)
    config_data = data.get("agent_config", data.get("agents", {}))

    name = proj_data.get("name", proj_data.get("project_name", "Imported Project"))
    description = proj_data.get("description", "")

    try:
        project = await crud.create_project(db, name=name, description=description)
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Project '{name}' already exists. Rename and retry.")
        raise HTTPException(status_code=500, detail=str(e))

    if config_data:
        await crud.update_agent_config(db, project.id, config_data)

    return project
