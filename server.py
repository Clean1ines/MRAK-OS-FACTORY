# CHANGED: Removed compute_content_hash, imported from utils if needed (currently not used)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
from routers import projects, artifacts, clarification, workflows, modes
import db
import os
# from utils.hash import compute_content_hash  # не используется сейчас

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MRAK-SERVER")

app = FastAPI(title="MRAK-OS Factory API")

# Include routers
app.include_router(projects.router)
app.include_router(artifacts.router)
app.include_router(clarification.router)
app.include_router(workflows.router)
app.include_router(modes.router)

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

# ==================== STATIC FILES ====================
from pathlib import Path

BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"
assets_dir = static_dir / "assets"

# Монтируем только если директория существует (для Docker-продакшена)
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
    # Игнорируем API пути
    if path.startswith("api/") or path.startswith("docs") or path.startswith("openapi"):
        return {"detail": "Not Found"}
    
    # Игнорируем favicon
    if path == "favicon.ico":
        return {"detail": "Not Found"}
    
    file_path = static_dir / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    
    return {"detail": "Not Found"}