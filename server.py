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

class GenerateArtifactRequest(BaseModel):
    artifact_type: str
    parent_id: str
    feedback: str = ""
    model: Optional[str] = None
    project_id: str
    existing_content: Optional[Any] = None  # может быть списком или словарём

class SavePackageRequest(BaseModel):
    project_id: str
    parent_id: str
    artifact_type: str
    content: Any  # для пакетов

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

@app.get("/api/latest_artifact")
async def latest_artifact(parent_id: str, type: str):
    """Возвращает последний артефакт указанного типа с заданным parent_id."""
    pkg = await get_last_package(parent_id, type)
    if pkg:
        return JSONResponse(content={
            "exists": True,
            "artifact_id": pkg['id'],
            "content": pkg['content']
        })
    else:
        return JSONResponse(content={"exists": False})

@app.post("/api/generate_artifact")
async def generate_artifact_endpoint(req: GenerateArtifactRequest):
    """Универсальный эндпоинт для генерации артефактов."""
    try:
        if req.artifact_type == "BusinessRequirementPackage":
            result = await orch.generate_business_requirements(
                analysis_id=req.parent_id,
                user_feedback=req.feedback,
                model_id=req.model,
                project_id=req.project_id,
                existing_requirements=req.existing_content
            )
        elif req.artifact_type == "ReqEngineeringAnalysis":
            result = await orch.generate_req_engineering_analysis(
                parent_id=req.parent_id,
                user_feedback=req.feedback,
                model_id=req.model,
                project_id=req.project_id,
                existing_analysis=req.existing_content
            )
        else:
            return JSONResponse(content={"error": "Unsupported artifact type"}, status_code=400)

        return JSONResponse(content={"result": result})
    except Exception as e:
        logger.error(f"Error generating artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/save_artifact_package")
async def save_artifact_package(req: SavePackageRequest):
    """Сохраняет пакет (список или словарь) как артефакт указанного типа."""
    try:
        last_pkg = await get_last_package(req.parent_id, req.artifact_type)
        if last_pkg:
            try:
                last_version = int(last_pkg['version'])
            except (ValueError, TypeError):
                last_version = 0
            version = str(last_version + 1)
            previous_versions = [last_pkg['id']]
        else:
            version = "1"
            previous_versions = []

        # Для пакетов требований добавляем локальные ID, если нужно
        if req.artifact_type in ["BusinessRequirementPackage", "FunctionalRequirementPackage"]:
            if isinstance(req.content, list):
                for i, r in enumerate(req.content):
                    if 'id' not in r:
                        r['id'] = f"req-{i+1:03d}"
            package_content = {
                "requirements": req.content,
                "generated_from": req.parent_id,
                "model": None,
                "version": version,
                "previous_versions": previous_versions
            }
        else:
            # Для анализа и других типов просто сохраняем как есть
            package_content = {
                "content": req.content,
                "generated_from": req.parent_id,
                "model": None,
                "version": version,
                "previous_versions": previous_versions
            }

        artifact_id = await save_artifact(
            artifact_type=req.artifact_type,
            content=package_content,
            owner="user",
            status="DRAFT",
            project_id=req.project_id,
            parent_id=req.parent_id
        )
        return JSONResponse(content={"id": artifact_id})
    except Exception as e:
        logger.error(f"Error saving package: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

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
