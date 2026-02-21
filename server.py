from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from orchestrator import MrakOrchestrator
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import db  # для проверки подключения
import json
import os
import hashlib

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
    existing_content: Optional[Any] = None

class SavePackageRequest(BaseModel):
    project_id: str
    parent_id: str
    artifact_type: str
    content: Any

class ValidateArtifactRequest(BaseModel):
    artifact_id: str
    status: str  # "VALIDATED" или "REJECTED"

class NextStepResponse(BaseModel):
    next_stage: str
    prompt_type: str
    parent_id: Optional[str]
    description: str

def compute_content_hash(content):
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

@app.on_event("startup")
async def startup_event():
    """Проверяем подключение к базе, но ничего не создаём."""
    logger.info("Starting up... Testing database connection.")
    try:
        conn = await db.get_connection()
        await conn.execute('SELECT 1')
        await conn.close()
        logger.info("Database connection OK.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

# ==================== ПРОЕКТЫ ====================

@app.get("/api/projects")
async def list_projects():
    projects = await db.get_projects()
    return JSONResponse(content=projects)

@app.post("/api/projects")
async def create_project_endpoint(project: ProjectCreate):
    project_id = await db.create_project(project.name, project.description)
    return JSONResponse(content={"id": project_id, "name": project.name})

@app.delete("/api/projects/{project_id}")
async def delete_project_endpoint(project_id: str):
    await db.delete_project(project_id)
    return JSONResponse(content={"status": "deleted"})

# ==================== АРТЕФАКТЫ ====================

@app.get("/api/projects/{project_id}/artifacts")
async def list_artifacts(project_id: str, type: Optional[str] = None):
    artifacts = await db.get_artifacts(project_id, type)
    return JSONResponse(content=artifacts)

@app.post("/api/artifact")
async def create_artifact(artifact: ArtifactCreate):
    try:
        if artifact.generate:
            parent = None
            if artifact.parent_id:
                parent = await db.get_artifact(artifact.parent_id)
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
            new_id = await db.save_artifact(
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
    pkg = await db.get_last_version_by_parent_and_type(parent_id, type)
    if pkg:
        return JSONResponse(content={
            "exists": True,
            "artifact_id": pkg['id'],
            "content": pkg['content']
        })
    else:
        return JSONResponse(content={"exists": False})

@app.post("/api/validate_artifact")
async def validate_artifact(req: ValidateArtifactRequest):
    """Изменяет статус артефакта (VALIDATED/REJECTED)."""
    try:
        await db.update_artifact_status(req.artifact_id, req.status)
        return JSONResponse(content={"status": "updated"})
    except Exception as e:
        logger.error(f"Error validating artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.delete("/api/artifact/{artifact_id}")
async def delete_artifact_endpoint(artifact_id: str):
    try:
        await db.delete_artifact(artifact_id)
        return JSONResponse(content={"status": "deleted"})
    except Exception as e:
        logger.error(f"Error deleting artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ==================== ГЕНЕРАЦИЯ АРТЕФАКТОВ ====================

@app.post("/api/generate_artifact")
async def generate_artifact_endpoint(req: GenerateArtifactRequest):
    try:
        # Используем универсальный метод, но поддерживаем старые специализированные для обратной совместимости
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
        elif req.artifact_type == "FunctionalRequirementPackage":
            result = await orch.generate_functional_requirements(
                analysis_id=req.parent_id,
                user_feedback=req.feedback,
                model_id=req.model,
                project_id=req.project_id,
                existing_requirements=req.existing_content
            )
        else:
            # Для всех остальных типов используем универсальный метод
            parent = await db.get_artifact(req.parent_id) if req.parent_id else None
            new_id = await orch.generate_artifact(
                artifact_type=req.artifact_type,
                user_input=req.feedback,
                parent_artifact=parent,
                model_id=req.model,
                project_id=req.project_id
            )
            return JSONResponse(content={"result": {"id": new_id}})

        return JSONResponse(content={"result": result})
    except Exception as e:
        logger.error(f"Error generating artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/save_artifact_package")
async def save_artifact_package(req: SavePackageRequest):
    try:
        new_hash = compute_content_hash(req.content)
        last_pkg = await db.get_last_version_by_parent_and_type(req.parent_id, req.artifact_type)
        if last_pkg and last_pkg.get('content_hash') == new_hash:
            return JSONResponse(content={"id": last_pkg['id'], "duplicate": True})

        last_pkg = await db.get_last_version_by_parent_and_type(req.parent_id, req.artifact_type)
        if last_pkg:
            try:
                last_version = int(last_pkg['version'])
            except (ValueError, TypeError):
                last_version = 0
            version = str(last_version + 1)
        else:
            version = "1"

        content_to_save = req.content
        if req.artifact_type in ["BusinessRequirementPackage", "FunctionalRequirementPackage"] and isinstance(content_to_save, list):
            import uuid
            for r in content_to_save:
                if 'id' not in r:
                    r['id'] = str(uuid.uuid4())

        artifact_id = await db.save_artifact(
            artifact_type=req.artifact_type,
            content=content_to_save,
            owner="user",
            status="DRAFT",
            project_id=req.project_id,
            parent_id=req.parent_id,
            content_hash=new_hash
        )
        return JSONResponse(content={"id": artifact_id})
    except Exception as e:
        logger.error(f"Error saving package: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ==================== ПРОСТОЙ РЕЖИМ ====================

@app.get("/api/workflow/next")
async def get_next_step(project_id: str):
    """Возвращает следующий рекомендуемый шаг для проекта в простом режиме."""
    try:
        step = await orch.get_next_step(project_id)
        if step:
            return JSONResponse(content=step)
        else:
            return JSONResponse(content={"next_stage": "finished", "description": "Проект завершён"})
    except Exception as e:
        logger.error(f"Error getting next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/workflow/execute_next")
async def execute_next_step(project_id: str, model: Optional[str] = None):
    """Выполняет следующий шаг: генерирует артефакт и возвращает его для предпросмотра."""
    try:
        step = await orch.get_next_step(project_id)
        if not step:
            return JSONResponse(content={"error": "No next step"}, status_code=400)
        if step['next_stage'] == 'idea':
            # Для идеи просто возвращаем информацию, что нужно ввести текст
            return JSONResponse(content={"action": "input_idea", "description": step['description']})
        # Генерируем артефакт
        if step['parent_id'] is None:
            # Нет родителя – значит, это первый шаг, но обычно так не бывает
            return JSONResponse(content={"error": "No parent"}, status_code=400)
        result = await orch.generate_artifact(
            artifact_type=step['prompt_type'],
            user_input="",  # фидбек пока пустой
            parent_artifact=await db.get_artifact(step['parent_id']),
            model_id=model,
            project_id=project_id
        )
        # В result должен быть ID созданного артефакта (черновик)
        # Получим его содержимое
        artifact = await db.get_artifact(result)
        return JSONResponse(content={
            "artifact_id": result,
            "artifact_type": step['prompt_type'],
            "content": artifact['content'] if artifact else None,
            "next_stage": step['next_stage']
        })
    except Exception as e:
        logger.error(f"Error executing next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ==================== МОДЕЛИ ====================

@app.get("/api/models")
async def get_models():
    models = orch.get_active_models()
    return JSONResponse(content=models)

# ==================== ЧАТ ====================

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
