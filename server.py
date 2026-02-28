# server.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
from routers import projects, artifacts, clarification, workflows, modes, auth
import db
import os

# Load environment variables before any other imports that might use them
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import structlog
from routers import projects, artifacts, clarification, workflows, modes, auth
import db

def validate_env():
    required = ["DATABASE_URL", "MASTER_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    if len(os.getenv("MASTER_KEY", "")) < 8:
        raise RuntimeError("MASTER_KEY must be at least 8 characters")
validate_env()

# #CHANGED: Configure structlog for JSON output with correlation_id support
# #FIX: inject_contextvars → merge_contextvars (structlog >= 22.1.0)
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
        # #ADDED: Merge contextvars into every log entry (replaces inject_contextvars)
        structlog.contextvars.merge_contextvars,
        # #ADDED: Render as JSON for production log aggregation
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# #CHANGED: Get structlog logger instance
logger = structlog.get_logger("MRAK-SERVER")

app = FastAPI(title="MRAK-OS Factory API")

# Include routers
app.include_router(projects.router)
app.include_router(artifacts.router)
app.include_router(clarification.router)
app.include_router(workflows.router)
app.include_router(modes.router)
app.include_router(auth.router)

# ==================== STARTUP ====================
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

# ==================== MIDDLEWARE ====================
@app.middleware("http")
async def validate_session_middleware(request: Request, call_next):
    # Skip auth for test mode
    if os.getenv("TEST_MODE") == "true":
        return await call_next(request)
    
    # Skip auth endpoints (don't require auth for login)
    if request.url.path.startswith("/api/auth"):
        logger.debug(f"Skipping auth for: {request.url.path}")
        return await call_next(request)
    
    # Skip static files
    if request.url.path.startswith("/assets"):
        return await call_next(request)
    
    # Check session for API requests
    if request.url.path.startswith("/api"):
        session_token = request.cookies.get("mrak_session")
        
        if not session_token:
            logger.warning(f"401: No session cookie for {request.url.path}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
        
        # Validate session
        from routers.auth import validate_session
        if not validate_session(session_token):
            logger.warning(f"401: Invalid session for {request.url.path}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Session expired or invalid"}
            )
        
        logger.debug(f"200: Valid session for {request.url.path}")
    
    return await call_next(request)

# ==================== STATIC FILES ====================
from pathlib import Path

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
    return {"error": "Frontend not built. Use Docker for production or run 'npm run dev' for development."}

@app.get("/{path:path}")
async def serve_spa(path: str):
    if path.startswith("api/") or path.startswith("docs") or path.startswith("openapi"):
        return {"detail": "Not Found"}
    
    if path == "favicon.ico":
        return {"detail": "Not Found"}
    
    file_path = static_dir / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    
    return {"detail": "Not Found"}