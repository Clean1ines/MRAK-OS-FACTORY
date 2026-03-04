"""
Integration tests for run_repository and node_execution_repository.
Uses real test database with transaction isolation.
"""
import pytest
import pytest_asyncio
import uuid
import json
import asyncpg
from typing import Dict, Any

from repositories import run_repository, node_execution_repository
from repositories.base import transaction

def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

# ----------------------------------------------------------------------
# Fixtures for creating prerequisite data
# ----------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_project(db_connection):
    proj_id = str(uuid.uuid4())
    proj_name = unique_name("Test Project")
    await db_connection.execute(
        "INSERT INTO projects (id, name, description) VALUES ($1, $2, $3)",
        proj_id, proj_name, "Test project"
    )
    return proj_id

@pytest_asyncio.fixture
async def test_workflow(db_connection, test_project):
    wf_id = str(uuid.uuid4())
    wf_name = unique_name("Test Workflow")
    await db_connection.execute(
        "INSERT INTO workflows (id, name, description, project_id, is_default) VALUES ($1, $2, $3, $4, $5)",
        wf_id, wf_name, "Test workflow", test_project, False
    )
    return wf_id

@pytest_asyncio.fixture
async def test_node(db_connection, test_workflow):
    node_record_id = str(uuid.uuid4())
    node_id = "test_node"
    config = {"system_prompt": "test", "user_prompt_template": "test", "required_input_types": []}
    await db_connection.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_record_id, test_workflow, node_id, "test_prompt", json.dumps(config), 0.0, 0.0
    )
    return node_record_id

@pytest_asyncio.fixture
async def test_run(db_connection, test_project, test_workflow):
    run_id = str(uuid.uuid4())
    await db_connection.execute(
        "INSERT INTO runs (id, project_id, workflow_id, status) VALUES ($1, $2, $3, $4)",
        run_id, test_project, test_workflow, "OPEN"
    )
    return run_id

@pytest_asyncio.fixture
async def test_artifact(db_connection, test_project):
    art_id = str(uuid.uuid4())
    content = {"text": "test content"}
    await db_connection.execute(
        "INSERT INTO artifacts (id, project_id, type, content, owner) VALUES ($1, $2, $3, $4, $5)",
        art_id, test_project, "test_type", json.dumps(content), "system"
    )
    return art_id

# ----------------------------------------------------------------------
# Tests for run_repository (unchanged, all passed)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_run_success(tx, test_project, test_workflow):
    run_id = await run_repository.create_run(
        project_id=test_project,
        workflow_id=test_workflow,
        created_by="tester",
        tx=tx
    )
    assert run_id is not None
    row = await tx.conn.fetchrow("SELECT * FROM runs WHERE id = $1", run_id)
    assert row["status"] == "OPEN"
    assert row["created_by"] == "tester"

@pytest.mark.asyncio
async def test_create_run_fk_violation_project(tx, test_workflow):
    fake_project = str(uuid.uuid4())
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await run_repository.create_run(
            project_id=fake_project,
            workflow_id=test_workflow,
            created_by=None,
            tx=tx
        )

@pytest.mark.asyncio
async def test_create_run_fk_violation_workflow(tx, test_project):
    fake_workflow = str(uuid.uuid4())
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await run_repository.create_run(
            project_id=test_project,
            workflow_id=fake_workflow,
            created_by=None,
            tx=tx
        )

@pytest.mark.asyncio
async def test_get_run_success(tx, test_run):
    run = await run_repository.get_run(test_run, tx=tx)
    assert run is not None
    assert run["id"] == test_run
    assert run["status"] == "OPEN"

@pytest.mark.asyncio
async def test_get_run_not_found(tx):
    fake_id = str(uuid.uuid4())
    run = await run_repository.get_run(fake_id, tx=tx)
    assert run is None

@pytest.mark.asyncio
async def test_update_run_status_open(tx, test_run):
    await run_repository.update_run_status(test_run, "OPEN", tx=tx)
    run = await run_repository.get_run(test_run, tx=tx)
    assert run["status"] == "OPEN"
    assert run["frozen_at"] is None
    assert run["archived_at"] is None

@pytest.mark.asyncio
async def test_update_run_status_frozen(tx, test_run):
    await run_repository.update_run_status(test_run, "FROZEN", tx=tx)
    run = await run_repository.get_run(test_run, tx=tx)
    assert run["status"] == "FROZEN"
    assert run["frozen_at"] is not None

@pytest.mark.asyncio
async def test_update_run_status_archived(tx, test_run):
    await run_repository.update_run_status(test_run, "ARCHIVED", tx=tx)
    run = await run_repository.get_run(test_run, tx=tx)
    assert run["status"] == "ARCHIVED"
    assert run["archived_at"] is not None

@pytest.mark.asyncio
async def test_list_runs_all(tx, test_project, test_workflow):
    run1 = await run_repository.create_run(test_project, test_workflow, tx=tx)
    run2 = await run_repository.create_run(test_project, test_workflow, tx=tx)
    runs = await run_repository.list_runs(tx=tx)
    run_ids = [r["id"] for r in runs]
    assert run1 in run_ids
    assert run2 in run_ids

@pytest.mark.asyncio
async def test_list_runs_filter_by_project(tx, test_project, test_workflow):
    other_proj = str(uuid.uuid4())
    await tx.conn.execute("INSERT INTO projects (id, name) VALUES ($1, $2)", other_proj, "Other")
    other_wf = str(uuid.uuid4())
    await tx.conn.execute("INSERT INTO workflows (id, name, project_id) VALUES ($1, $2, $3)", other_wf, "Other WF", other_proj)
    run_in_other = await run_repository.create_run(other_proj, other_wf, tx=tx)
    run_main1 = await run_repository.create_run(test_project, test_workflow, tx=tx)
    run_main2 = await run_repository.create_run(test_project, test_workflow, tx=tx)
    runs = await run_repository.list_runs(project_id=test_project, tx=tx)
    run_ids = [r["id"] for r in runs]
    assert run_main1 in run_ids
    assert run_main2 in run_ids
    assert run_in_other not in run_ids

@pytest.mark.asyncio
async def test_list_runs_empty(tx):
    proj = str(uuid.uuid4())
    await tx.conn.execute("INSERT INTO projects (id, name) VALUES ($1, $2)", proj, "Empty")
    runs = await run_repository.list_runs(project_id=proj, tx=tx)
    assert runs == []

# ----------------------------------------------------------------------
# Tests for node_execution_repository
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_node_execution_success_no_inputs(tx, test_run, test_node):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key1",
        input_artifact_ids=None,
        tx=tx
    )
    assert exec_id is not None
    row = await tx.conn.fetchrow("SELECT * FROM node_executions WHERE id = $1", exec_id)
    assert row["status"] == "PROCESSING"
    assert row["idempotency_key"] == "key1"
    assert row["input_artifact_ids"] is None

@pytest.mark.asyncio
async def test_create_node_execution_with_empty_list(tx, test_run, test_node):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key2",
        input_artifact_ids=[],
        tx=tx
    )
    row = await tx.conn.fetchrow("SELECT input_artifact_ids FROM node_executions WHERE id = $1", exec_id)
    assert row["input_artifact_ids"] == "[]"

@pytest.mark.asyncio
async def test_create_node_execution_with_artifacts(tx, test_run, test_node, test_artifact):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key3",
        input_artifact_ids=[test_artifact],
        tx=tx
    )
    row = await tx.conn.fetchrow("SELECT input_artifact_ids FROM node_executions WHERE id = $1", exec_id)
    assert json.loads(row["input_artifact_ids"]) == [test_artifact]

@pytest.mark.asyncio
async def test_create_node_execution_unique_violation(tx, test_run, test_node):
    # Создаём родительское выполнение, чтобы иметь не-NULL parent_execution_id
    parent_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="parent",
        tx=tx
    )
    # Первое дочернее
    await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=parent_id,
        idempotency_key="dup",
        tx=tx
    )
    # Второе с тем же ключом должно вызвать ошибку
    with pytest.raises(asyncpg.UniqueViolationError):
        await node_execution_repository.create_node_execution(
            run_id=test_run,
            node_definition_id=test_node,
            parent_execution_id=parent_id,
            idempotency_key="dup",
            tx=tx
        )

@pytest.mark.asyncio
async def test_create_node_execution_fk_violation_run(tx, test_node):
    fake_run = str(uuid.uuid4())
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await node_execution_repository.create_node_execution(
            run_id=fake_run,
            node_definition_id=test_node,
            parent_execution_id=None,
            idempotency_key="key",
            tx=tx
        )

@pytest.mark.asyncio
async def test_create_node_execution_fk_violation_node(tx, test_run):
    fake_node = str(uuid.uuid4())
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await node_execution_repository.create_node_execution(
            run_id=test_run,
            node_definition_id=fake_node,
            parent_execution_id=None,
            idempotency_key="key",
            tx=tx
        )

@pytest.mark.asyncio
async def test_get_node_execution_success(tx, test_run, test_node):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key",
        input_artifact_ids=[str(uuid.uuid4())],
        tx=tx
    )
    exec_dict = await node_execution_repository.get_node_execution(exec_id, tx=tx)
    assert exec_dict is not None
    assert exec_dict["id"] == exec_id
    assert exec_dict["run_id"] == test_run
    assert exec_dict["node_definition_id"] == test_node
    assert isinstance(exec_dict["input_artifact_ids"], list)

@pytest.mark.asyncio
async def test_get_node_execution_not_found(tx):
    fake_id = str(uuid.uuid4())
    exec_dict = await node_execution_repository.get_node_execution(fake_id, tx=tx)
    assert exec_dict is None

@pytest.mark.asyncio
async def test_update_node_execution_status_without_output(tx, test_run, test_node):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key",
        tx=tx
    )
    await node_execution_repository.update_node_execution_status(exec_id, "COMPLETED", tx=tx)
    exec_dict = await node_execution_repository.get_node_execution(exec_id, tx=tx)
    assert exec_dict["status"] == "COMPLETED"
    assert exec_dict["output_artifact_id"] is None

@pytest.mark.asyncio
async def test_update_node_execution_status_with_output(tx, test_run, test_node, test_artifact):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key",
        tx=tx
    )
    await node_execution_repository.update_node_execution_status(
        exec_id, "COMPLETED", output_artifact_id=test_artifact, tx=tx
    )
    exec_dict = await node_execution_repository.get_node_execution(exec_id, tx=tx)
    assert exec_dict["status"] == "COMPLETED"
    assert exec_dict["output_artifact_id"] == test_artifact

@pytest.mark.asyncio
async def test_find_existing_execution_found(tx, test_run, test_node):
    exec_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="findme",
        tx=tx
    )
    found = await node_execution_repository.find_existing_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="findme",
        tx=tx
    )
    assert found is not None
    assert found["id"] == exec_id

@pytest.mark.asyncio
async def test_find_existing_execution_with_parent(tx, test_run, test_node):
    parent_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="parent",
        tx=tx
    )
    child_id = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=parent_id,
        idempotency_key="child",
        tx=tx
    )
    found = await node_execution_repository.find_existing_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=parent_id,
        idempotency_key="child",
        tx=tx
    )
    assert found is not None
    assert found["id"] == child_id

@pytest.mark.asyncio
async def test_find_existing_execution_not_found(tx, test_run, test_node):
    found = await node_execution_repository.find_existing_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="nonexistent",
        tx=tx
    )
    assert found is None

@pytest.mark.asyncio
async def test_get_validated_execution_for_node_found(tx, test_run, test_node):
    exec1 = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key1",
        tx=tx
    )
    exec2 = await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key2",
        tx=tx
    )
    await tx.conn.execute("UPDATE node_executions SET status = 'VALIDATED' WHERE id = $1", exec2)
    validated = await node_execution_repository.get_validated_execution_for_node(
        run_id=test_run,
        node_definition_id=test_node,
        tx=tx
    )
    assert validated is not None
    assert validated["id"] == exec2

@pytest.mark.asyncio
async def test_get_validated_execution_for_node_not_found(tx, test_run, test_node):
    await node_execution_repository.create_node_execution(
        run_id=test_run,
        node_definition_id=test_node,
        parent_execution_id=None,
        idempotency_key="key",
        tx=tx
    )
    validated = await node_execution_repository.get_validated_execution_for_node(
        run_id=test_run,
        node_definition_id=test_node,
        tx=tx
    )
    assert validated is None
