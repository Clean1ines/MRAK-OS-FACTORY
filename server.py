import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import structlog

from routers import projects, artifacts, workflows, auth
from routers import runs
import db
from groq_client import GroqClient
from artifact_service import ArtifactService
from dependencies import init_dependencies

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
init_dependencies(artifact_service)

# Подключение роутеров
app.include_router(projects.router)
app.include_router(artifacts.router)
#app.include_router(clarification.router)
app.include_router(workflows.router)
app.include_router(auth.router)
app.include_router(runs.router)

# Модуль modes временно отключён — будет переписан позже
# app.include_router(modes.router)

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
    if request.url.path.startswith("/api/auth"):
        request_logger.debug("Skipping auth for endpoint")
        return await call_next(request)
    if request.url.path.startswith("/assets"):
        return await call_next(request)
    if request.url.path == "/health":
        request_logger.debug("Skipping auth for health endpoint")
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
    file_path = static_dir / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    logger.debug("404: Path not found", path=path)
    return {"detail": "Not Found"}
