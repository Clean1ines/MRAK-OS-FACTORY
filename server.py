# CHANGED: Removed compute_content_hash, imported from utils if needed (currently not used)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
app.mount("/", StaticFiles(directory=".", html=True), name="static")
