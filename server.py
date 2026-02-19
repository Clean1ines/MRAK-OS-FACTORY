from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from orchestrator import MrakOrchestrator
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from db import init_db, get_projects, create_project, get_artifacts, save_artifact, get_artifact, get_last_package
import json
import asyncpg
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MRAK-SERVER")

app = FastAPI(title="MRAK-OS Factory API")
orch = MrakOrchestrator()

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ArtifactCreate(BaseModel):
    project_id: str
    artifact_type: str
    content: str
    parent_id: Optional[str] = None
    generate: bool = False
    model: Optional[str] = None

class BusinessReqGenRequest(BaseModel):
    analysis_id: str
    feedback: str = ""
    model: Optional[str] = None
    project_id: str
    existing_requirements: Optional[List[Dict]] = None
    existing_package_id: Optional[str] = None

class SaveRequirementsRequest(BaseModel):
    project_id: str
    parent_id: str
    requirements: List[Dict[str, Any]]

@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

@app.get("/api/projects")
async def list_projects():
    projects = await get_projects()
    return JSONResponse(content=projects)

@app.post("/api/projects")
async def create_project_endpoint(project: ProjectCreate):
    project_id = await create_project(project.name, project.description)
    return JSONResponse(content={"id": project_id, "name": project.name})

@app.get("/api/projects/{project_id}/artifacts")
async def list_artifacts(project_id: str, type: Optional[str] = None):
    artifacts = await get_artifacts(project_id, type)
    return JSONResponse(content=artifacts)

@app.post("/api/artifact")
async def create_artifact(artifact: ArtifactCreate):
    try:
        if artifact.generate:
            parent = None
            if artifact.parent_id:
                parent = await get_artifact(artifact.parent_id)
                if not parent:
                    return JSONResponse(content={"error": "Parent artifact not found"}, status_code=404)
            new_id = await orch.generate_artifact(
                artifact_type=artifact.artifact_type,
                user_input=artifact.content,
                parent_artifact=parent,
                model_id=artifact.model,
                project_id=artifact.project_id
            )
            return JSONResponse(content={"id": new_id, "generated": True})
        else:
            content_data = {"text": artifact.content}
            new_id = await save_artifact(
                artifact_type=artifact.artifact_type,
                content=content_data,
                owner="user",
                status="DRAFT",
                project_id=artifact.project_id,
                parent_id=artifact.parent_id
            )
            return JSONResponse(content={"id": new_id, "generated": False})
    except Exception as e:
        logger.error(f"Error creating artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/generate_business_requirements")
async def generate_business_requirements(req: BusinessReqGenRequest):
    try:
        existing = None
        if req.existing_package_id:
            pkg = await get_artifact(req.existing_package_id)
            if pkg and 'requirements' in pkg['content']:
                existing = pkg['content']['requirements']
        elif req.existing_requirements:
            existing = req.existing_requirements

        requirements = await orch.generate_business_requirements(
            analysis_id=req.analysis_id,
            user_feedback=req.feedback,
            model_id=req.model,
            project_id=req.project_id,
            existing_requirements=existing
        )
        return JSONResponse(content={"requirements": requirements})
    except Exception as e:
        logger.error(f"Error generating business requirements: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/save_business_requirements")
async def save_business_requirements(req: SaveRequirementsRequest):
    try:
        last_pkg = await get_last_package(req.parent_id, "BusinessRequirementPackage")
        version = (last_pkg['version'] + 1) if last_pkg else 1
        previous_versions = [last_pkg['id']] if last_pkg else []

        for i, r in enumerate(req.requirements):
            if 'id' not in r:
                r['id'] = f"req-{i+1:03d}"

        package_content = {
            "requirements": req.requirements,
            "generated_from": req.parent_id,
            "model": None,
            "version": version,
            "previous_versions": previous_versions
        }
        artifact_id = await save_artifact(
            artifact_type="BusinessRequirementPackage",
            content=package_content,
            owner="user",
            status="DRAFT",
            project_id=req.project_id,
            parent_id=req.parent_id
        )
        return JSONResponse(content={"id": artifact_id})
    except Exception as e:
        logger.error(f"Error saving requirements: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/latest_requirement_package")
async def latest_requirement_package(parent_id: str):
    pkg = await get_last_package(parent_id, "BusinessRequirementPackage")
    if pkg:
        return JSONResponse(content={
            "exists": True,
            "package_id": pkg['id'],
            "requirements": pkg['content'].get('requirements', [])
        })
    else:
        return JSONResponse(content={"exists": False})

@app.get("/api/models")
async def get_models():
    models = orch.get_active_models()
    return JSONResponse(content=models)

@app.post("/api/analyze")
async def analyze(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON received: {e}")
        return JSONResponse(content={"error": "Invalid JSON body"}, status_code=400)

    prompt = data.get("prompt")
    mode = data.get("mode", "01_CORE")
    model = data.get("model")
    project_id = data.get("project_id")

    if not prompt:
        return JSONResponse(content={"error": "Prompt is required"}, status_code=400)

    if not model:
        model = "llama-3.3-70b-versatile"

    sys_prompt = await orch.get_system_prompt(mode)

    if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
        logger.error(f"Prompt fetch failed for mode {mode}: {sys_prompt}")
        async def error_stream():
            yield f"🔴 **SYSTEM_CRITICAL_ERROR**: {sys_prompt}\n"
            yield "Check your .env (GITHUB_TOKEN) and repository URLs."
        return StreamingResponse(error_stream(), media_type="text/plain")

    logger.info(f"Starting stream: Mode={mode}, Model={model}, Project={project_id}")

    return StreamingResponse(
        orch.stream_analysis(prompt, sys_prompt, model, mode, project_id=project_id),
        media_type="text/plain",
    )

app.mount("/", StaticFiles(directory=".", html=True), name="static")
