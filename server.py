from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from logic import MrakOrchestrator
import logging
from pydantic import BaseModel
from typing import Optional
from db import init_db, get_projects, create_project

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MRAK-SERVER")

app = FastAPI(title="MRAK-OS Factory API")
orch = MrakOrchestrator()

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

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
