from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from orchestrator import MrakOrchestrator
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import db
import json
import os
import hashlib
import datetime  # ADDED: for timestamps

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

# ========== ADDED: Pydantic models for clarification ==========
class StartClarificationRequest(BaseModel):
    project_id: str
    target_artifact_type: str
    model: Optional[str] = None  # если не указано, будет использована модель по умолчанию

class MessageRequest(BaseModel):
    message: str

class ClarificationSessionResponse(BaseModel):
    id: str
    project_id: str
    target_artifact_type: str
    history: List[Dict[str, Any]]
    status: str
    context_summary: Optional[str] = None
    final_artifact_id: Optional[str] = None
    created_at: str
    updated_at: str

def compute_content_hash(content):
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

@app.on_event("startup")
async def startup_event():
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
            parent = await db.get_artifact(req.parent_id) if req.parent_id else None
            new_id = await orch.generate_artifact(
                artifact_type=req.artifact_type,
                user_input=req.feedback,
                parent_artifact=parent,
                model_id=req.model,
                project_id=req.project_id
            )
            # Получаем полный артефакт из БД
            artifact = await db.get_artifact(new_id)
            if artifact:
                return JSONResponse(content={"result": artifact['content']})
            else:
                return JSONResponse(content={"result": {"id": new_id}})

        return JSONResponse(content={"result": result})
    except Exception as e:
        logger.error(f"Error generating artifact: {e}", exc_info=True)
        return JSONResponse(content={"error": f"Internal server error: {str(e)}"}, status_code=500)

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

# ==================== ИСТОРИЯ СООБЩЕНИЙ ====================

@app.get("/api/projects/{project_id}/messages")
async def get_project_messages(project_id: str):
    """Возвращает все артефакты типа LLMResponse для проекта, отсортированные по времени."""
    artifacts = await db.get_artifacts(project_id, artifact_type="LLMResponse")
    # Сортируем по created_at (старые сначала)
    artifacts.sort(key=lambda x: x['created_at'])
    return JSONResponse(content=artifacts)

# ==================== ПРОСТОЙ РЕЖИМ ====================

@app.get("/api/workflow/next")
async def get_next_step(project_id: str):
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
    try:
        step = await orch.get_next_step(project_id)
        if not step:
            return JSONResponse(content={"error": "No next step"}, status_code=400)
        if step['next_stage'] == 'idea':
            return JSONResponse(content={"action": "input_idea", "description": step['description']})

        existing = await db.get_last_version_by_parent_and_type(step['parent_id'], step['prompt_type'])
        if existing and existing['status'] == 'VALIDATED':
            return JSONResponse(content={
                "artifact_id": existing['id'],
                "artifact_type": step['prompt_type'],
                "content": existing['content'],
                "parent_id": step['parent_id'],
                "next_stage": step['next_stage'],
                "existing": True
            })

        parent = await db.get_artifact(step['parent_id']) if step.get('parent_id') else None
        if not parent:
            return JSONResponse(content={"error": "Parent artifact not found"}, status_code=404)

        new_id = await orch.generate_artifact(
            artifact_type=step['prompt_type'],
            user_input="",
            parent_artifact=parent,
            model_id=model,
            project_id=project_id
        )
        artifact = await db.get_artifact(new_id)
        return JSONResponse(content={
            "artifact_id": new_id,
            "artifact_type": step['prompt_type'],
            "content": artifact['content'] if artifact else None,
            "parent_id": step['parent_id'],
            "next_stage": step['next_stage'],
            "existing": False
        })
    except Exception as e:
        logger.error(f"Error executing next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ==================== МОДЕЛИ И РЕЖИМЫ ====================

@app.get("/api/models")
async def get_models():
    models = orch.get_active_models()
    return JSONResponse(content=models)

@app.get("/api/modes")
async def get_available_modes():
    return [
        {"id": "01_CORE", "name": "01: CORE_SYSTEM", "default": True},
        {"id": "02_IDEA_CLARIFIER", "name": "02: IDEA_CLARIFIER"},
        {"id": "03_PRODUCT_COUNCIL", "name": "03: PRODUCT_COUNCIL"},
        {"id": "04_BUSINESS_REQ_GEN", "name": "04: BUSINESS_REQ_GEN"},
        {"id": "05_REQ_ENG_COUNCIL", "name": "05: REQ_ENG_COUNCIL"},
        {"id": "06_SYSTEM_REQ_GEN", "name": "06: SYSTEM_REQ_GEN"},
        {"id": "07_QA_COUNCIL", "name": "07: QA_COUNCIL"},
        {"id": "08_ARCHITECTURE_COUNCIL", "name": "08: ARCHITECTURE_COUNCIL"},
        {"id": "09_CODE_TASK_GEN", "name": "09: CODE_TASK_GEN"},
        {"id": "10_CODE_GEN", "name": "10: CODE_GEN"},
        {"id": "11_TEST_GEN", "name": "11: TEST_GEN"},
        {"id": "12_FAILURE_DETECTOR", "name": "12: FAILURE_DETECTOR"},
        {"id": "13_SELF_ANALYSIS_FACTORY", "name": "13: SELF_ANALYSIS_FACTORY"},
        {"id": "14_PROMPT_ENGINEERING_COUNCIL", "name": "14: PROMPT_ENGINEERING_COUNCIL"},
        {"id": "15_ALGORITHM_COUNCIL", "name": "15: ALGORITHM_COUNCIL"},
        {"id": "16_UI_UX_COUNCIL", "name": "16: UI_UX_COUNCIL"},
        {"id": "17_SOFT_ENG_COUNCIL", "name": "17: SOFT_ENG_COUNCIL"},
        {"id": "18_TRANSLATOR", "name": "18: TRANSLATOR"},
        {"id": "19_INTEGRATION_PLAN", "name": "19: INTEGRATION_PLAN"},
        {"id": "20_SECURITY_REQ_GEN", "name": "20: SECURITY_REQ_GEN"},
        {"id": "21_THREAT_MODELING_ASSISTANT", "name": "21: THREAT_MODELING_ASSISTANT"},
        {"id": "22_INFRASTRUCTURE_SPEC_GEN", "name": "22: INFRASTRUCTURE_SPEC_GEN"},
        {"id": "23_OBSERVABILITY_SPEC_GEN", "name": "23: OBSERVABILITY_SPEC_GEN"},
        {"id": "24_TECH_DESIGN_DOC_GEN", "name": "24: TECH_DESIGN_DOC_GEN"},
        {"id": "25_USER_DOC_GEN", "name": "25: USER_DOC_GEN"},
        {"id": "26_API_DOC_GEN", "name": "26: API_DOC_GEN"},
        {"id": "27_UAT_SCRIPT_GEN", "name": "27: UAT_SCRIPT_GEN"},
        {"id": "28_JIRA_ISSUE_FORMATTER", "name": "28: JIRA_ISSUE_FORMATTER"},
        {"id": "29_PROJECT_STATUS_REPORTER", "name": "29: PROJECT_STATUS_REPORTER"},
        {"id": "30_INCIDENT_POST_MORTEM_GEN", "name": "30: INCIDENT_POST_MORTEM_GEN"},
        {"id": "31_KNOWLEDGE_QUERY_ASSISTANT", "name": "31: KNOWLEDGE_QUERY_ASSISTANT"},
        {"id": "32_CHANGE_IMPACT_ANALYZER", "name": "32: CHANGE_IMPACT_ANALYZER"},
        {"id": "33_FEATURE_TO_USER_STORY_GEN", "name": "33: FEATURE_TO_USER_STORY_GEN"},
        {"id": "34_RESEARCH_METODOLOGY_GEN", "name": "34: RESEARCH_METODOLOGY_GEN"},
        {"id": "35_ANALYSIS_SUMMARIZER", "name": "35: ANALYSIS_SUMMARIZER"},
        {"id": "36_REQUIREMENT_SUMMARIZER", "name": "36: REQUIREMENT_SUMMARIZER"},
        {"id": "37_SYSTEM_REQUIREMENTS_SUMMARIZER", "name": "37: SYSTEM_REQUIREMENTS_SUMMARIZER"},
        {"id": "38_CODE_CONTEXT_SUMMARIZER", "name": "38: CODE_CONTEXT_SUMMARIZER"},
    ]

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

# ==================== ADDED: Clarification session endpoints ====================

@app.post("/api/clarification/start", response_model=ClarificationSessionResponse)
async def start_clarification(req: StartClarificationRequest):
    """Создаёт новую сессию уточнения и генерирует первое сообщение ассистента."""
    # Проверяем существование проекта
    project = await db.get_project(req.project_id)
    if not project:
        return JSONResponse(content={"error": "Project not found"}, status_code=404)

    # Определяем режим промпта по типу артефакта
    mode = orch.type_to_mode.get(req.target_artifact_type)
    if not mode:
        return JSONResponse(content={"error": f"No prompt mode found for artifact type {req.target_artifact_type}"}, status_code=400)

    # Получаем системный промпт
    sys_prompt = await orch.get_system_prompt(mode)
    if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
        return JSONResponse(content={"error": sys_prompt}, status_code=500)

    # Создаём сессию в БД
    session_id = await db.create_clarification_session(req.project_id, req.target_artifact_type)

    # Формируем сообщения для LLM: системный промпт + пустой пользовательский запрос?
    # Для первого сообщения ассистент должен задать вопрос, поэтому отправляем системный промпт и, возможно, инструкцию "Начни диалог".
    # Используем модель из запроса или дефолтную
    model = req.model or "llama-3.3-70b-versatile"
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "Начни уточняющий диалог. Задай первый вопрос, чтобы понять идею пользователя."}
    ]
    try:
        assistant_message = await orch.get_chat_completion(messages, model)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return JSONResponse(content={"error": "Failed to generate first message"}, status_code=500)

    # Добавляем сообщение ассистента в историю
    await db.add_message_to_session(session_id, "assistant", assistant_message)

    # Получаем обновлённую сессию
    session = await db.get_clarification_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session created but not found"}, status_code=500)

    return ClarificationSessionResponse(
        id=session['id'],
        project_id=session['project_id'],
        target_artifact_type=session['target_artifact_type'],
        history=session['history'],
        status=session['status'],
        context_summary=session.get('context_summary'),
        final_artifact_id=session.get('final_artifact_id'),
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )

@app.post("/api/clarification/{session_id}/message", response_model=ClarificationSessionResponse)
async def add_message(session_id: str, req: MessageRequest):
    """Добавляет сообщение пользователя, генерирует ответ ассистента и обновляет историю."""
    session = await db.get_clarification_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)

    if session['status'] != 'active':
        return JSONResponse(content={"error": "Session is not active"}, status_code=400)

    # Добавляем сообщение пользователя
    await db.add_message_to_session(session_id, "user", req.message)

    # Получаем обновлённую историю
    session = await db.get_clarification_session(session_id)
    history = session['history']

    # Определяем режим промпта по типу артефакта
    mode = orch.type_to_mode.get(session['target_artifact_type'])
    if not mode:
        return JSONResponse(content={"error": f"No prompt mode found for artifact type {session['target_artifact_type']}"}, status_code=500)

    # Получаем системный промпт
    sys_prompt = await orch.get_system_prompt(mode)
    if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
        return JSONResponse(content={"error": sys_prompt}, status_code=500)

    # Формируем полную историю для LLM
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in history:
        messages.append({"role": msg['role'], "content": msg['content']})

    # FIXED: Используем фиксированную модель, так как в запросе её нет
    model = "llama-3.3-70b-versatile"
    try:
        assistant_message = await orch.get_chat_completion(messages, model)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return JSONResponse(content={"error": "Failed to generate assistant message"}, status_code=500)

    # Добавляем ответ ассистента в историю
    await db.add_message_to_session(session_id, "assistant", assistant_message)

    # Получаем финальную версию сессии
    session = await db.get_clarification_session(session_id)

    return ClarificationSessionResponse(
        id=session['id'],
        project_id=session['project_id'],
        target_artifact_type=session['target_artifact_type'],
        history=session['history'],
        status=session['status'],
        context_summary=session.get('context_summary'),
        final_artifact_id=session.get('final_artifact_id'),
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )

@app.get("/api/clarification/{session_id}", response_model=ClarificationSessionResponse)
async def get_clarification_session_endpoint(session_id: str):
    """Возвращает текущее состояние сессии."""
    session = await db.get_clarification_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)
    return ClarificationSessionResponse(
        id=session['id'],
        project_id=session['project_id'],
        target_artifact_type=session['target_artifact_type'],
        history=session['history'],
        status=session['status'],
        context_summary=session.get('context_summary'),
        final_artifact_id=session.get('final_artifact_id'),
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )

@app.post("/api/clarification/{session_id}/complete")
async def complete_clarification_session(session_id: str):
    """Помечает сессию как завершённую (заглушка для будущей генерации артефакта)."""
    session = await db.get_clarification_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)
    if session['status'] != 'active':
        return JSONResponse(content={"error": "Session already completed"}, status_code=400)

    await db.update_clarification_session(session_id, status="completed")
    return JSONResponse(content={"status": "completed", "session_id": session_id})

@app.get("/api/projects/{project_id}/clarification/active")
async def get_active_sessions(project_id: str):
    """Возвращает все активные сессии для проекта (для восстановления после перезагрузки)."""
    sessions = await db.list_active_sessions_for_project(project_id)
    return JSONResponse(content=[
        {
            "id": s['id'],
            "target_artifact_type": s['target_artifact_type'],
            "created_at": s['created_at'],
            "updated_at": s['updated_at']
        }
        for s in sessions
    ])

app.mount("/", StaticFiles(directory=".", html=True), name="static")