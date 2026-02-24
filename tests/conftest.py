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

# Используем отдельную тестовую БД если есть, иначе основную
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

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
    """Соединение с БД в транзакции, которая откатывается после теста."""
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await conn.execute("BEGIN")
    try:
        yield conn
    finally:
        await conn.execute("ROLLBACK")  # ← ОТКАТ всех изменений
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
        project_id, "Test Project", "Project for testing"
    )
    try:
        return {"id": project_id, "name": "Test Project"}
    finally:
        # Очистка после теста
        await db_connection.execute("DELETE FROM projects WHERE id = $1", project_id)

@pytest_asyncio.fixture
async def test_workflow(db_connection, test_project) -> Dict[str, str]:
    workflow_id = str(uuid.uuid4())
    await db_connection.execute(
        "INSERT INTO workflows (id, name, description, is_default) VALUES ($1, $2, $3, $4)",
        workflow_id, "Test Workflow", "WF for testing", False
    )
    try:
        return {"id": workflow_id, "name": "Test Workflow"}
    finally:
        await db_connection.execute("DELETE FROM workflows WHERE id = $1", workflow_id)