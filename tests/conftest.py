import os
import pytest
import pytest_asyncio
import asyncpg
from fastapi.testclient import TestClient
from typing import Dict, AsyncGenerator
import uuid

# Устанавливаем переменную окружения ДО импорта приложения
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Импортируем приложение после установки переменной
from server import app
import db

@pytest.fixture(scope="function")
def sync_client():
    """Синхронный клиент для API тестов (не требует asyncio)."""
    with TestClient(app) as client:
        yield client

@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator:
    """Асинхронный клиент для тестов, которым нужен async/await."""
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
        await conn.execute("ROLLBACK")
        await conn.close()

@pytest_asyncio.fixture
async def test_project(db_connection) -> Dict[str, str]:
    """Создаёт тестовый проект (будет откатан после теста)."""
    project_id = str(uuid.uuid4())
    await db_connection.execute(
        "INSERT INTO projects (id, name, description) VALUES ($1, $2, $3)",
        project_id, "Test Project", "Project for testing"
    )
    return {"id": project_id, "name": "Test Project"}

@pytest_asyncio.fixture
async def test_workflow(db_connection, test_project) -> Dict[str, str]:
    """Создаёт тестовый workflow (будет откатан после теста)."""
    workflow_id = str(uuid.uuid4())
    await db_connection.execute(
        "INSERT INTO workflows (id, name, description, is_default) VALUES ($1, $2, $3, $4)",
        workflow_id, "Test Workflow", "WF for testing", False
    )
    return {"id": workflow_id, "name": "Test Workflow"}