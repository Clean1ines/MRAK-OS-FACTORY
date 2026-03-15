import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import structlog

from routers import projects, artifacts, workflows, auth, truth
from routers import runs
from routers import modes
from routers import telegram
import db
from groq_client import GroqClient
from artifact_service import ArtifactService
from dependencies import init_dependencies

# импорты новых сервисов
from prompt_loader import PromptLoader
from prompt_service import PromptService
from session_service import SessionService
from services.llm_stream_service import LLMStreamService

# импорт для Telegram webhook
from telegram_bot.handlers import get_application, handle_webhook, init_application
from telegram_bot.config import PUBLIC_URL

load_dotenv()

def validate_env():
    required = ["DATABASE_URL", "MASTER_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    if len(os.getenv("MASTER_KEY", "")) < 8:
        raise RuntimeError("MASTER_KEY must be at least 8 characters")
validate_env()

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.contextvars.merge_contextvars,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("MRAK-SERVER")
app = FastAPI(title="MRAK-OS Factory API")

@app.get("/health")
async def health():
    return {"status": "ok"}

# Инициализация сервисов
groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
artifact_service = ArtifactService(groq_client=groq_client)

prompt_loader = PromptLoader(gh_token=os.getenv("GITHUB_TOKEN"))
mode_map = {}
prompt_service = PromptService(groq_client, prompt_loader, mode_map)
llm_stream_service = LLMStreamService(groq_client, prompt_loader)
session_service = SessionService()

init_dependencies(
    artifact_service,
    prompt_service,
    llm_stream_service,
    session_service
)

# Подключение роутеров
app.include_router(projects.router)
app.include_router(artifacts.router)
app.include_router(workflows.router)
app.include_router(auth.router)
app.include_router(truth.router)
app.include_router(runs.router)
app.include_router(telegram.router)
app.include_router(modes.router)

# ==================== TELEGRAM WEBHOOK ====================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Эндпоинт для приёма обновлений от Telegram."""
    try:
        data = await request.json()
        await handle_webhook(data)
        return JSONResponse(status_code=200, content={"ok": True})
    except Exception as e:
        logger.error("Error processing Telegram webhook", exc_info=e)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ==================== STARTUP EVENT ====================
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up... Testing database connection.")
    try:
        conn = await db.get_connection()
        await conn.execute('SELECT 1')
        await conn.close()
        logger.info("Database connection OK.")
    except Exception as e:
        logger.error("Database connection failed", exc_info=e, error=str(e))
    
    # Инициализация Telegram Application и установка вебхука
    try:
        bot_app = get_application()
        await init_application()   # <-- добавили вызов инициализации
        webhook_url = f"{PUBLIC_URL.rstrip('/')}/webhook"
        await bot_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info(f"Telegram webhook set to {webhook_url}")
    except Exception as e:
        logger.error("Failed to set Telegram webhook", exc_info=e)

# ==================== MIDDLEWARE ====================
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_logger = logger.bind(correlation_id=correlation_id, path=request.url.path, method=request.method)
    request_logger.info("Request started", remote_addr=request.client.host if request.client else None)
    try:
        response = await call_next(request)
        request_logger.info("Request completed", status_code=response.status_code)
        response.headers["X-Request-ID"] = correlation_id
        return response
    except Exception as e:
        request_logger.error("Request failed with 5xx", exc_info=e, error=str(e))
        raise

@app.middleware("http")
async def validate_session_middleware(request: Request, call_next):
    request_logger = logger.bind(path=request.url.path)
    if os.getenv("TEST_MODE") == "true":
        return await call_next(request)
    if request.url.path.startswith("/api/auth") or request.url.path == "/api/models":
        request_logger.debug("Skipping auth for endpoint")
        return await call_next(request)
    if request.url.path.startswith("/assets"):
        return await call_next(request)
    if request.url.path == "/health":
        request_logger.debug("Skipping auth for health endpoint")
        return await call_next(request)
    if request.url.path == "/webhook":
        request_logger.debug("Skipping auth for Telegram webhook")
        return await call_next(request)
    # НОВОЕ: пропускаем manager-reply
    if request.url.path.startswith("/api/executions/") and request.url.path.endswith("/manager-reply"):
        request_logger.debug("Skipping auth for manager reply endpoint")
        return await call_next(request)
    if request.url.path.startswith("/api"):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            request_logger.warning("401: Missing or invalid Authorization header")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required: send 'Authorization: Bearer <token>'"}
            )
        session_token = auth_header[7:]
        if not session_token:
            request_logger.warning("401: Empty session token")
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        from routers.auth import validate_session
        if not validate_session(session_token):
            request_logger.warning("401: Invalid session token")
            return JSONResponse(status_code=401, content={"detail": "Session expired or invalid"})
        request_logger.debug("200: Valid session")
    return await call_next(request)
    
# ==================== STATIC FILES ====================
BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"
assets_dir = static_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/")
async def serve_frontend():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    logger.error("Frontend not built", path=str(index_path))
    return {"error": "Frontend not built. Use Docker for production or run 'npm run dev' for development."}

@app.get("/{path:path}")
async def serve_spa(path: str):
    if path.startswith("api/") or path.startswith("docs") or path.startswith("openapi") or path == "health":
        return {"detail": "Not Found"}
    if path == "favicon.ico":
        return {"detail": "Not Found"}
    if path == "webhook":
        # POST на /webhook уже обработан выше, GET возвращаем 405
        return JSONResponse(status_code=405, content={"detail": "Method Not Allowed"})
    file_path = static_dir / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    logger.debug("404: Path not found", path=path)
    return {"detail": "Not Found"}

@app.get("/debug/routes")
async def debug_routes():
    from fastapi.routing import APIRoute
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(f"{list(route.methods)} {route.path}")
    return routes  