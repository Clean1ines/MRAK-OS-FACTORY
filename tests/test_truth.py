"""
Integration tests for truth endpoint and snapshot updates (ADR-006).
Uses real database, mocks only external LLM via groq_client.
"""
import pytest
import uuid
import time
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from server import app
from dependencies import get_artifact_service
from repositories.base import transaction

client = TestClient(app)

def unique_name(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

# ----------------------------------------------------------------------
# Fixture to mock groq_client (external LLM) – same as in test_artifacts.py
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_groq_client(mocker):
    """Mock the groq_client to return a successful response."""
    mock = MagicMock()
    mock.create_completion = MagicMock()
    mock.create_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"result": "ok"}'))]
    )
    from dependencies import get_artifact_service
    real_service = get_artifact_service()
    mocker.patch.object(real_service, 'groq_client', mock)
    return mock

# ----------------------------------------------------------------------
# Tests for /truth endpoint
# ----------------------------------------------------------------------

def test_truth_empty_project(sync_client):
    """Project with no validated executions should return empty list."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Empty")})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    resp = sync_client.get(f"/api/projects/{project_id}/truth")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert "as_of" in data
    assert data["nodes"] == []

def test_truth_single_node(sync_client):
    """Project with one active node."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Single")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_data = {
        "node_id": "test_node",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test Node"
        },
        "position_x": 0,
        "position_y": 0
    }
    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json=node_data)
    node_record_id = node_resp.json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    exec_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key1",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec_id = exec_resp.json()["id"]

    time.sleep(0.5)
    validate_resp = sync_client.post(f"/api/executions/{exec_id}/validate")
    assert validate_resp.status_code == 200

    truth_resp = sync_client.get(f"/api/projects/{project_id}/truth")
    assert truth_resp.status_code == 200
    data = truth_resp.json()
    assert len(data["nodes"]) == 1
    node = data["nodes"][0]
    assert node["node_id"] == node_record_id
    assert node["execution_id"] == exec_id
    assert "artifact" in node
    assert node["artifact"]["status"] == "ACTIVE"

def test_truth_two_nodes(sync_client):
    """Project with two active nodes (different node_definition_id)."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("TwoNodes")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node1_id = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "node1",
        "prompt_key": "test1",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Node 1"
        },
        "position_x": 0, "position_y": 0
    }).json()["id"]
    node2_id = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "node2",
        "prompt_key": "test2",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Node 2"
        },
        "position_x": 100, "position_y": 0
    }).json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    for node_record_id in [node1_id, node2_id]:
        exec_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
            "idempotency_key": str(uuid.uuid4()),
            "parent_execution_id": None,
            "input_artifact_ids": []
        })
        exec_id = exec_resp.json()["id"]
        time.sleep(0.5)
        sync_client.post(f"/api/executions/{exec_id}/validate")

    truth_resp = sync_client.get(f"/api/projects/{project_id}/truth")
    assert truth_resp.status_code == 200
    nodes = truth_resp.json()["nodes"]
    assert len(nodes) == 2
    node_ids = {n["node_id"] for n in nodes}
    assert node_ids == {node1_id, node2_id}

def test_truth_supersede(sync_client):
    """When a new execution for the same node is validated, snapshot updates and old becomes SUPERSEDED."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Supersede")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "test",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test"
        },
        "position_x": 0, "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    # First execution
    exec1_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key1",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec1_id = exec1_resp.json()["id"]
    time.sleep(0.5)
    validate1_resp = sync_client.post(f"/api/executions/{exec1_id}/validate")
    assert validate1_resp.status_code == 200

    truth1 = sync_client.get(f"/api/projects/{project_id}/truth").json()
    assert len(truth1["nodes"]) == 1
    assert truth1["nodes"][0]["execution_id"] == exec1_id

    # Second execution (different run, same node)
    run2_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run2_id = run2_resp.json()["id"]
    exec2_resp = sync_client.post(f"/api/runs/{run2_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key2",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec2_id = exec2_resp.json()["id"]
    time.sleep(0.5)
    validate2_resp = sync_client.post(f"/api/executions/{exec2_id}/validate")
    assert validate2_resp.status_code == 200

    truth2 = sync_client.get(f"/api/projects/{project_id}/truth").json()
    assert len(truth2["nodes"]) == 1
    assert truth2["nodes"][0]["execution_id"] == exec2_id

    async def check_old_status():
        from repositories.node_execution_repository import get_node_execution
        async with transaction() as tx:
            exec1 = await get_node_execution(exec1_id, tx=tx)
        return exec1["status"]
    status1 = asyncio.run(check_old_status())
    assert status1 == "SUPERSEDED"

def test_truth_as_of(sync_client):
    """as_of parameter returns historical state."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("AsOf")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "test",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test"
        },
        "position_x": 0, "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    # First execution
    exec1_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key1",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec1_id = exec1_resp.json()["id"]
    time.sleep(0.5)
    validate1_resp = sync_client.post(f"/api/executions/{exec1_id}/validate")
    assert validate1_resp.status_code == 200

    # Получаем точное время валидации первого выполнения из truth
    truth_after_first = sync_client.get(f"/api/projects/{project_id}/truth").json()
    assert len(truth_after_first["nodes"]) == 1
    validated_at_first = truth_after_first["nodes"][0]["validated_at"]
    # Преобразуем строку ISO в datetime (с сохранением таймзоны)
    from datetime import datetime, timezone
    dt_first = datetime.fromisoformat(validated_at_first.replace('Z', '+00:00'))

    # Wait a bit, then second execution
    time.sleep(1)
    exec2_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key2",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec2_id = exec2_resp.json()["id"]
    time.sleep(0.5)
    validate2_resp = sync_client.post(f"/api/executions/{exec2_id}/validate")
    assert validate2_resp.status_code == 200

    truth_now = sync_client.get(f"/api/projects/{project_id}/truth").json()
    assert truth_now["nodes"][0]["execution_id"] == exec2_id

    # as_of с временем первого выполнения (включительно) должно вернуть его
    as_of_time = dt_first.isoformat().replace('+00:00', '') + '+00:00'  # полная точность
    truth_as_of = sync_client.get(f"/api/projects/{project_id}/truth", params={"as_of": as_of_time})
    assert truth_as_of.status_code == 200
    data = truth_as_of.json()
    assert len(data["nodes"]) == 1, f"Nodes: {data['nodes']}"
    assert data["nodes"][0]["execution_id"] == exec1_id

    as_of_early = "2000-01-01T00:00:00+00:00"
    truth_early = sync_client.get(f"/api/projects/{project_id}/truth", params={"as_of": as_of_early}).json()
    assert truth_early["nodes"] == []

    resp = sync_client.get(f"/api/projects/{project_id}/truth", params={"as_of": "invalid-date"})
    assert resp.status_code == 422

# ----------------------------------------------------------------------
# Tests for validation and snapshot update
# ----------------------------------------------------------------------

def test_validate_updates_snapshot(sync_client):
    """After validation, snapshot should contain the correct data."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Snapshot")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "test",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test"
        },
        "position_x": 0, "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    exec_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec_id = exec_resp.json()["id"]

    time.sleep(0.5)
    sync_client.post(f"/api/executions/{exec_id}/validate")

    async def check_snapshot():
        async with transaction() as tx:
            row = await tx.conn.fetchrow("""
                SELECT * FROM project_truth_snapshot
                WHERE project_id = $1 AND node_definition_id = $2
            """, project_id, node_record_id)
            return dict(row) if row else None
    snap = asyncio.run(check_snapshot())
    assert snap is not None
    assert str(snap["execution_id"]) == exec_id

def test_validate_without_artifact_raises(sync_client):
    """Validating an execution without artifact should fail (CHECK constraint)."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("NoArtifact")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "test",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test"
        },
        "position_x": 0, "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    exec_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec_id = exec_resp.json()["id"]

    time.sleep(0.5)

    # Manually delete the artifact and set output_artifact_id to NULL
    async def remove_artifact():
        async with transaction() as tx:
            row = await tx.conn.fetchrow("SELECT output_artifact_id FROM node_executions WHERE id = $1", exec_id)
            if row and row["output_artifact_id"]:
                await tx.conn.execute("DELETE FROM artifacts WHERE id = $1", row["output_artifact_id"])
            await tx.conn.execute(
                "UPDATE node_executions SET output_artifact_id = NULL WHERE id = $1",
                exec_id
            )
    asyncio.run(remove_artifact())

    import asyncpg
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        sync_client.post(f"/api/executions/{exec_id}/validate")

def test_validate_frozen_run(sync_client):
    """Validating an execution in a frozen run should return 409 and not update snapshot."""
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Frozen")})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "test",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test"
        },
        "position_x": 0, "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    run_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run_id = run_resp.json()["id"]

    exec_resp = sync_client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec_id = exec_resp.json()["id"]

    time.sleep(0.5)
    sync_client.post(f"/api/runs/{run_id}/freeze")

    resp = sync_client.post(f"/api/executions/{exec_id}/validate")
    assert resp.status_code == 409
    assert "Run is not OPEN" in resp.json()["detail"]

# ----------------------------------------------------------------------
# Concurrency test (optional, may be slow)
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_validation(sync_client):
    """Two concurrent validations for the same node – one succeeds, the other fails."""
    proj_name = unique_name("Concurrent")
    proj_resp = sync_client.post("/api/projects", json={"name": proj_name, "description": ""})
    project_id = proj_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": unique_name("WF"),
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    workflow_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{workflow_id}/nodes", json={
        "node_id": "test",
        "prompt_key": "test",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "test",
            "title": "Test"
        },
        "position_x": 0, "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    run1_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run1_id = run1_resp.json()["id"]
    run2_resp = sync_client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    run2_id = run2_resp.json()["id"]

    exec1_resp = sync_client.post(f"/api/runs/{run1_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key1",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec1_id = exec1_resp.json()["id"]
    exec2_resp = sync_client.post(f"/api/runs/{run2_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key2",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    exec2_id = exec2_resp.json()["id"]

    time.sleep(1)

    async def validate(eid):
        def sync_validate():
            return sync_client.post(f"/api/executions/{eid}/validate")
        return await asyncio.to_thread(sync_validate)

    results = await asyncio.gather(validate(exec1_id), validate(exec2_id), return_exceptions=True)

    statuses = []
    for r in results:
        if isinstance(r, Exception):
            statuses.append(500)
        else:
            statuses.append(r.status_code)

    assert 200 in statuses
    assert any(s != 200 for s in statuses)
