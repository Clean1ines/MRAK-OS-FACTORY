# tests/conftest.py
import os
import pytest
import pytest_asyncio
import asyncpg
from fastapi.testclient import TestClient
from typing import Dict, AsyncGenerator
import uuid
from dotenv import load_dotenv
from types import SimpleNamespace

load_dotenv()

# FIX #5: Force use of TEST_DATABASE_URL for isolation
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    # Fallback to DATABASE_URL but warn
    TEST_DATABASE_URL = os.getenv("DATABASE_URL")
    print("⚠️ WARNING: TEST_DATABASE_URL not set, using DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set")

# Override DATABASE_URL for the app during tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# #ADDED: Enable test mode to bypass authentication middleware
os.environ["TEST_MODE"] = "true"

from server import app
import db

@pytest.fixture(scope="function")
def sync_client():
    with TestClient(app) as client:
        yield client

@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator:
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def db_connection():
    """FIX #5: Connection with transaction rollback for test isolation."""
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await conn.execute("BEGIN")
    try:
        yield conn
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()

@pytest_asyncio.fixture
async def tx(db_connection):
    """Provides a transaction object with .conn attribute for repository functions."""
    yield SimpleNamespace(conn=db_connection)

@pytest_asyncio.fixture
async def test_project(db_connection) -> Dict[str, str]:
    project_id = str(uuid.uuid4())
    await db_connection.execute(
        "INSERT INTO projects (id, name, description) VALUES ($1, $2, $3)",
        project_id, f"Test Project {project_id[:8]}", "Project for testing"
    )
    try:
        return {"id": project_id, "name": f"Test Project {project_id[:8]}"}
    finally:
        await db_connection.execute("DELETE FROM projects WHERE id = $1", project_id)

@pytest_asyncio.fixture
async def test_workflow(db_connection, test_project) -> Dict[str, str]:
    workflow_id = str(uuid.uuid4())
    await db_connection.execute(
        "INSERT INTO workflows (id, name, description, is_default) VALUES ($1, $2, $3, $4)",
        workflow_id, f"Test Workflow {workflow_id[:8]}", "WF for testing", False
    )
    try:
        return {"id": workflow_id, "name": f"Test Workflow {workflow_id[:8]}"}
    finally:
        await db_connection.execute("DELETE FROM workflows WHERE id = $1", workflow_id)