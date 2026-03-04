# tests/conftest.py
import os
import subprocess
import pytest
import pytest_asyncio
import asyncpg
from fastapi.testclient import TestClient
from typing import Dict, AsyncGenerator
import uuid
from dotenv import load_dotenv
from types import SimpleNamespace

from pathlib import Path

# Load .env.test if exists, otherwise .env
env_path = Path(__file__).parent.parent / '.env.test'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # fallback to .env

# #ADDED: Automatically start Docker container if not running
def _ensure_test_database_container():
    """
    Ensure PostgreSQL test database container is running before tests.
    This runs at module import time, before any test executes.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'ensure_test_db.sh')
    if os.path.exists(script_path):
        try:
            result = subprocess.run(
                ['bash', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            # Always print output for debugging
            print(result.stdout)
            if result.returncode != 0:
                print(f"❌ Failed to start database: {result.stderr}")
                raise RuntimeError(f"Could not start test database: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout starting test database container")
        except FileNotFoundError:
            pass  # Script not found, assume DB is already running

# #CRITICAL: Run this FIRST before any DB operations
_ensure_test_database_container()

# FIX #5: Force use of TEST_DATABASE_URL for isolation
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    TEST_DATABASE_URL = os.getenv("DATABASE_URL")
    print("⚠️ WARNING: TEST_DATABASE_URL not set, using DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set")

# Override DATABASE_URL for the app during tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TEST_MODE"] = "true"

from server import app
import db


def _apply_schema():
    """Применяет полную схему из дампа к тестовой базе."""
    schema_file = Path(__file__).parent / "test_schema.sql"
    if not schema_file.exists():
        raise RuntimeError(
            f"Schema file {schema_file} not found. "
            "Run: pg_dump -s $DATABASE_URL > tests/test_schema.sql"
        )

    # Явно передаём URL в команду psql, без export
    cmd = ["psql", TEST_DATABASE_URL, "-f", str(schema_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("Failed to apply schema to test database")
    print("✅ Test database schema applied")

# Применяем схему один раз при импорте conftest.py
_apply_schema()


# === ADDED: Session-scoped autouse fixture to clean all tables before tests ===
@pytest.fixture(scope="session", autouse=True)
def clean_test_db():
    """
    Очищает все таблицы в тестовой БД перед запуском тестовой сессии.
    Выполняется один раз перед всеми тестами, после создания таблиц.
    """
    import asyncpg
    import asyncio

    async def clean():
        conn = await asyncpg.connect(TEST_DATABASE_URL)
        # Получаем список всех пользовательских таблиц в схеме public
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename != 'spatial_ref_sys'
        """)
        if tables:
            table_names = ', '.join(f'"{t["tablename"]}"' for t in tables)
            await conn.execute(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;")
        await conn.close()

    asyncio.run(clean())
    yield  # тесты выполняются
    # после тестов ничего не делаем (очистка перед следующей сессией произойдёт снова)
# =============================================================================


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