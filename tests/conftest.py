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


# #ADDED: Sync wrapper for async DB initialization (runs after container is started)
def _initialize_database_sync():
    """
    Synchronous wrapper to initialize database tables before tests.
    This runs at module import time, guaranteeing tables exist.
    """
    import asyncio

    async def init_db():
        conn = await asyncpg.connect(TEST_DATABASE_URL)
        try:
            # Check if tables exist
            tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN
                ('projects', 'workflows', 'workflow_nodes', 'workflow_edges',
                 'artifacts', 'artifact_types', 'clarification_sessions')
            """)

            if len(tables) < 7:
                print(f"🔧 Found {len(tables)}/7 tables, creating missing tables...")

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS public.projects (
                        id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                        name text NOT NULL,
                        description text,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now()
                    );

                    CREATE TABLE IF NOT EXISTS public.artifact_types (
                        type text NOT NULL PRIMARY KEY,
                        schema jsonb NOT NULL,
                        icon text,
                        allowed_parents text[] DEFAULT '{}'::text[] NOT NULL,
                        requires_clarification boolean DEFAULT false NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS public.workflows (
                        id uuid NOT NULL PRIMARY KEY,
                        name text NOT NULL,
                        description text,
                        project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
                        is_default boolean DEFAULT false,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now()
                    );

                    CREATE TABLE IF NOT EXISTS public.workflow_nodes (
                        id uuid NOT NULL PRIMARY KEY,
                        workflow_id uuid NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
                        node_id text NOT NULL,
                        prompt_key text NOT NULL,
                        position_x double precision NOT NULL,
                        position_y double precision NOT NULL,
                        config jsonb DEFAULT '{}'::jsonb NOT NULL,
                        UNIQUE(workflow_id, node_id)
                    );

                    CREATE TABLE IF NOT EXISTS public.workflow_edges (
                        id uuid NOT NULL PRIMARY KEY,
                        workflow_id uuid NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
                        source_node text NOT NULL,
                        target_node text NOT NULL,
                        source_output text DEFAULT 'output'::text NOT NULL,
                        target_input text DEFAULT 'input'::text NOT NULL,
                        FOREIGN KEY (workflow_id, source_node) REFERENCES public.workflow_nodes(workflow_id, node_id) ON DELETE CASCADE,
                        FOREIGN KEY (workflow_id, target_node) REFERENCES public.workflow_nodes(workflow_id, node_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS public.artifacts (
                        id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                        project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
                        type text NOT NULL,
                        name text,
                        content jsonb NOT NULL,
                        content_hash character varying(64),
                        parent_id uuid REFERENCES public.artifacts(id) ON DELETE SET NULL,
                        owner character varying(100),
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now(),
                        created_by text DEFAULT 'system'::text
                    );

                    CREATE TABLE IF NOT EXISTS public.clarification_sessions (
                        id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                        project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
                        target_artifact_type text NOT NULL,
                        status text DEFAULT 'active'::text NOT NULL,
                        system_prompt text NOT NULL,
                        user_prompt_template text,
                        context_summary text,
                        history jsonb DEFAULT '[]'::jsonb NOT NULL,
                        node_id uuid REFERENCES public.workflow_nodes(id),
                        final_artifact_id uuid REFERENCES public.artifacts(id) ON DELETE SET NULL,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now()
                    );

                    CREATE INDEX IF NOT EXISTS idx_workflow_nodes_workflow ON public.workflow_nodes USING btree (workflow_id);
                    CREATE INDEX IF NOT EXISTS idx_workflow_edges_workflow ON public.workflow_edges USING btree (workflow_id);
                    CREATE INDEX IF NOT EXISTS idx_clarification_sessions_project ON public.clarification_sessions USING btree (project_id);
                    CREATE INDEX IF NOT EXISTS idx_clarification_sessions_status ON public.clarification_sessions USING btree (status);
                """)
                print("✅ Database tables created/verified")
            else:
                print("✅ All database tables exist")
        finally:
            await conn.close()

    # Run async init synchronously at import time
    asyncio.run(init_db())

# #CRITICAL: Run DB initialization AFTER container is started
_initialize_database_sync()


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
