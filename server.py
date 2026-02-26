# server.py
# CHANGED: Replaced standard logging with structlog for JSON output + correlation_id

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import structlog
from routers import projects, artifacts, clarification, workflows, modes, auth
import db
import os
import uuid

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

# #ADDED: Health check endpoint
@app.get("/health")
async def health():
    """
    Health check endpoint for load balancers and monitoring.
    Returns {"status": "ok"} if service is alive.
    
    Returns:
        dict: Status indicator.
    """
    return {"status": "ok"}

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
    """
    Initialize database connection on startup.
    
    Logs connection status via structlog. Exits silently on failure
    to allow health-check-based orchestration.
    """
    # #CHANGED: Use structlog logger
    logger.info("Starting up... Testing database connection.")
    try:
        conn = await db.get_connection()
        await conn.execute('SELECT 1')
        await conn.close()
        logger.info("Database connection OK.")
    except Exception as e:
        # #CHANGED: Log exception with stack trace for 5xx errors
        logger.error("Database connection failed", exc_info=e, error=str(e))

# ==================== MIDDLEWARE ====================
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Inject correlation_id into logs and response headers for request tracing.
    
    Args:
        request: FastAPI Request object.
        call_next: Next middleware/handler in chain.
    
    Returns:
        Response with X-Request-ID header.
    """
    # #ADDED: Extract or generate correlation_id for request tracing
    correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # #ADDED: Bind correlation_id to structlog context for this request
    request_logger = logger.bind(correlation_id=correlation_id, path=request.url.path, method=request.method)

    # #ADDED: Log request start
    request_logger.info("Request started", remote_addr=request.client.host if request.client else None)

    try:
        response = await call_next(request)
        # #ADDED: Log response status
        request_logger.info("Request completed", status_code=response.status_code)
        # #ADDED: Add correlation_id to response headers for frontend/debugging
        response.headers["X-Request-ID"] = correlation_id
        return response
    except Exception as e:
        # #ADDED: Log 5xx errors with full stack trace
        request_logger.error("Request failed with 5xx", exc_info=e, error=str(e))
        raise

@app.middleware("http")
async def validate_session_middleware(request: Request, call_next):
    """
    Validate session token from Authorization header (Bearer scheme ONLY).
    
    Cookies are NOT supported due to cross-domain/cors constraints.
    Token must be present in sessionStorage on client and sent as:
        Authorization: Bearer <session_token>
    
    Args:
        request: FastAPI Request object.
        call_next: Next middleware/handler in chain.
    
    Returns:
        Response if auth fails, else continues to handler.
    
    Raises:
        HTTPException: 401 if token missing or invalid.
    """
    # #CHANGED: Use structlog logger with request context
    request_logger = logger.bind(path=request.url.path)

    # Skip auth for test mode
    if os.getenv("TEST_MODE") == "true":
        return await call_next(request)

    # Skip auth endpoints (don't require auth for login)
    if request.url.path.startswith("/api/auth"):
        request_logger.debug("Skipping auth for endpoint")
        return await call_next(request)

    # Skip static files
    if request.url.path.startswith("/assets"):
        return await call_next(request)

    # Skip health endpoint (doesn't require auth)
    if request.url.path == "/health":
        request_logger.debug("Skipping auth for health endpoint")
        return await call_next(request)

    # Check session for API requests
    if request.url.path.startswith("/api"):
        # #CHANGED: Accept ONLY Bearer token from Authorization header (NO cookie fallback)
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            request_logger.warning("401: Missing or invalid Authorization header (expected 'Bearer <token>')")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required: send 'Authorization: Bearer <token>'"}
            )
        
        session_token = auth_header[7:]  # Remove "Bearer " prefix

        if not session_token:
            request_logger.warning("401: Empty session token")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )

        # Validate session
        from routers.auth import validate_session
        if not validate_session(session_token):
            request_logger.warning("401: Invalid session token")
            return JSONResponse(
                status_code=401,
                content={"detail": "Session expired or invalid"}
            )

        request_logger.debug("200: Valid session")

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
    """
    Serve frontend index.html for SPA routing.
    
    Returns:
        FileResponse: index.html if exists, else error JSON.
    """
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # #CHANGED: Use structlog for error logging
    logger.error("Frontend not built", path=str(index_path))
    return {"error": "Frontend not built. Use Docker for production or run 'npm run dev' for development."}

@app.get("/{path:path}")
async def serve_spa(path: str):
    """
    Handle SPA client-side routing: serve index.html for unknown paths.
    
    Args:
        path: URL path segment.
    
    Returns:
        FileResponse or JSON error.
    """
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

    # #CHANGED: Log 404 with structlog
    logger.debug("404: Path not found", path=path)
    return {"detail": "Not Found"}