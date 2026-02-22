# ADDED: Project endpoints
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import db
from repositories.base import transaction
from schemas import ProjectCreate  # CHANGED: import from schemas

router = APIRouter(prefix="/api", tags=["projects"])

@router.get("/projects")
async def list_projects():
    projects = await db.get_projects()
    return JSONResponse(content=projects)

@router.post("/projects")
async def create_project_endpoint(project: ProjectCreate):
    async with transaction() as tx:
        project_id = await db.create_project(project.name, project.description, tx=tx)
    return JSONResponse(content={"id": project_id, "name": project.name})

@router.delete("/projects/{project_id}")
async def delete_project_endpoint(project_id: str):
    async with transaction() as tx:
        await db.delete_project(project_id, tx=tx)
    return JSONResponse(content={"status": "deleted"})
