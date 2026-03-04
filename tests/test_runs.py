"""
Debug version of runs tests with unique project names to avoid 400 errors.
Все вызовы execute_node используют record_id узла (UUID), а не логическое имя.
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def unique_name(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

def test_create_run_success():
    """Создаёт проект, воркфлоу и run в одном тесте с отладочным выводом."""
    print("\n=== test_create_run_success ===")
    # Создаём проект
    proj_name = unique_name("Debug Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": "test"})
    print(f"Create project status: {proj_resp.status_code}")
    if proj_resp.status_code != 201:
        print(f"Project creation failed: {proj_resp.text}")
        assert False, "Project creation failed"
    project_id = proj_resp.json()["id"]
    print(f"Project ID: {project_id}")

    # Создаём воркфлоу
    wf_resp = client.post("/api/workflows", json={
        "name": unique_name("Debug Workflow"),
        "description": "test",
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    print(f"Create workflow status: {wf_resp.status_code}")
    if wf_resp.status_code != 201:
        print(f"Workflow creation failed: {wf_resp.text}")
        assert False, "Workflow creation failed"
    workflow_id = wf_resp.json()["id"]
    print(f"Workflow ID: {workflow_id}")

    # Создаём run
    run_resp = client.post("/api/runs", json={
        "project_id": project_id,
        "workflow_id": workflow_id
    })
    print(f"Create run status: {run_resp.status_code}")
    print(f"Run response text: {run_resp.text}")
    assert run_resp.status_code == 201, f"Expected 201, got {run_resp.status_code}: {run_resp.text}"
    data = run_resp.json()
    assert data["project_id"] == project_id
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "OPEN"
    print("Run created successfully:", data)

def test_create_run_missing_project():
    """Пытаемся создать run с несуществующим project_id."""
    print("\n=== test_create_run_missing_project ===")
    fake_project = str(uuid.uuid4())
    fake_workflow = str(uuid.uuid4())
    resp = client.post("/api/runs", json={
        "project_id": fake_project,
        "workflow_id": fake_workflow
    })
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    assert resp.status_code == 400
    assert "project not found" in resp.json()["detail"].lower()

def test_create_run_missing_workflow():
    """Пытаемся создать run с несуществующим workflow_id."""
    print("\n=== test_create_run_missing_workflow ===")
    # Сначала создаём проект
    proj_name = unique_name("Project for missing workflow")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    fake_workflow = str(uuid.uuid4())
    resp = client.post("/api/runs", json={
        "project_id": project_id,
        "workflow_id": fake_workflow
    })
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    assert resp.status_code == 400
    assert "workflow not found" in resp.json()["detail"].lower()

def test_get_run_success():
    """Создаём run и получаем его."""
    print("\n=== test_get_run_success ===")
    # Создаём проект и воркфлоу
    proj_name = unique_name("Get Run Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Get Run WF")
    wf_resp = client.post("/api/workflows", json={
        "name": wf_name,
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    assert wf_resp.status_code == 201
    workflow_id = wf_resp.json()["id"]

    # Создаём run
    run_resp = client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Получаем run
    get_resp = client.get(f"/api/runs/{run_id}")
    print(f"Get run status: {get_resp.status_code}")
    print(f"Get run response: {get_resp.text}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == run_id
    assert data["status"] == "OPEN"

def test_execute_node_success():
    """Создаём узел и выполняем его, используя record_id узла."""
    print("\n=== test_execute_node_success ===")
    # Создаём проект, воркфлоу, узел
    proj_name = unique_name("Execute Node Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Execute Node WF")
    # Создаём воркфлоу без узлов, потом добавим узел отдельно
    wf_resp = client.post("/api/workflows", json={
        "name": wf_name,
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    assert wf_resp.status_code == 201
    workflow_id = wf_resp.json()["id"]

    # Добавляем узел
    node_data = {
        "node_id": "test_node",
        "prompt_key": "test_prompt",
        "config": {
            "system_prompt": "You are a helpful assistant.",
            "user_prompt_template": "Context: {all_artifacts}\nUser input: {user_input}",
            "required_input_types": []
        },
        "position_x": 0,
        "position_y": 0
    }
    node_resp = client.post(f"/api/workflows/{workflow_id}/nodes", json=node_data)
    assert node_resp.status_code == 201
    node_record_id = node_resp.json()["id"]  # это UUID записи
    print(f"Node record ID: {node_record_id}")

    # Создаём run
    run_resp = client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Выполняем узел (используем record_id)
    exec_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "key1",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    print(f"Execute node status: {exec_resp.status_code}")
    print(f"Execute node response: {exec_resp.text}")
    assert exec_resp.status_code == 200
    data = exec_resp.json()
    assert data["run_id"] == run_id
    assert data["node_definition_id"] == node_record_id
    assert data["status"] == "PROCESSING"
    assert data["idempotency_key"] == "key1"

def test_execute_node_idempotent():
    """Два одинаковых запроса должны вернуть одно и то же выполнение."""
    print("\n=== test_execute_node_idempotent ===")
    # Создаём проект, воркфлоу, узел, run
    proj_name = unique_name("Idempotent Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Idempotent WF")
    wf_resp = client.post("/api/workflows", json={
        "name": wf_name,
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    assert wf_resp.status_code == 201
    workflow_id = wf_resp.json()["id"]

    # Добавляем узел
    node_data = {
        "node_id": "test_node",
        "prompt_key": "test_prompt",
        "config": {"system_prompt": "test", "user_prompt_template": "test", "required_input_types": []},
        "position_x": 0,
        "position_y": 0
    }
    node_resp = client.post(f"/api/workflows/{workflow_id}/nodes", json=node_data)
    assert node_resp.status_code == 201
    node_record_id = node_resp.json()["id"]

    run_resp = client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    payload = {
        "idempotency_key": "idem_key",
        "parent_execution_id": None,
        "input_artifact_ids": []
    }
    resp1 = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json=payload)
    print(f"First execute status: {resp1.status_code}")
    print(f"First response: {resp1.text}")
    assert resp1.status_code == 200
    id1 = resp1.json()["id"]

    resp2 = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json=payload)
    print(f"Second execute status: {resp2.status_code}")
    print(f"Second response: {resp2.text}")
    assert resp2.status_code == 200
    id2 = resp2.json()["id"]
    assert id1 == id2
    print("Idempotency works, IDs match:", id1)

def test_validate_execution_success():
    """Создаём выполнение, завершаем (COMPLETED) и валидируем."""
    print("\n=== test_validate_execution_success ===")
    # Создаём проект, воркфлоу, узел, run
    proj_name = unique_name("Validate Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Validate WF")
    wf_resp = client.post("/api/workflows", json={
        "name": wf_name,
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    assert wf_resp.status_code == 201
    workflow_id = wf_resp.json()["id"]

    # Добавляем узел
    node_data = {
        "node_id": "test_node",
        "prompt_key": "test_prompt",
        "config": {"system_prompt": "test", "user_prompt_template": "test", "required_input_types": []},
        "position_x": 0,
        "position_y": 0
    }
    node_resp = client.post(f"/api/workflows/{workflow_id}/nodes", json=node_data)
    assert node_resp.status_code == 201
    node_record_id = node_resp.json()["id"]

    run_resp = client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Создаём выполнение
    exec_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "val_key",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    assert exec_resp.status_code == 200
    exec_id = exec_resp.json()["id"]

    # Вручную переводим в COMPLETED (обычно это делает фоновая задача)
    import asyncpg
    import os
    import asyncio

    async def set_completed():
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            await conn.execute("UPDATE node_executions SET status = 'COMPLETED' WHERE id = $1", exec_id)
        finally:
            await conn.close()
    asyncio.run(set_completed())

    # Валидируем
    validate_resp = client.post(f"/api/executions/{exec_id}/validate")
    print(f"Validate status: {validate_resp.status_code}")
    print(f"Validate response: {validate_resp.text}")
    assert validate_resp.status_code == 200
    data = validate_resp.json()
    assert data["id"] == exec_id
    assert data["status"] == "VALIDATED"

def test_freeze_run_success():
    """Создаём run и замораживаем его."""
    print("\n=== test_freeze_run_success ===")
    proj_name = unique_name("Freeze Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Freeze WF")
    wf_resp = client.post("/api/workflows", json={
        "name": wf_name,
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    assert wf_resp.status_code == 201
    workflow_id = wf_resp.json()["id"]

    run_resp = client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    freeze_resp = client.post(f"/api/runs/{run_id}/freeze")
    print(f"Freeze status: {freeze_resp.status_code}")
    print(f"Freeze response: {freeze_resp.text}")
    assert freeze_resp.status_code == 200
    assert freeze_resp.json()["status"] == "frozen"

    # Проверяем через GET
    get_resp = client.get(f"/api/runs/{run_id}")
    assert get_resp.json()["status"] == "FROZEN"

def test_supersede_execution_success():
    """Создаём два выполнения, первое валидируем, затем вторым supersede."""
    print("\n=== test_supersede_execution_success ===")
    # Создаём проект, воркфлоу, узел, run
    proj_name = unique_name("Supersede Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Supersede WF")
    wf_resp = client.post("/api/workflows", json={
        "name": wf_name,
        "project_id": project_id,
        "nodes": [],
        "edges": []
    })
    assert wf_resp.status_code == 201
    workflow_id = wf_resp.json()["id"]

    # Добавляем узел
    node_data = {
        "node_id": "test_node",
        "prompt_key": "test_prompt",
        "config": {"system_prompt": "test", "user_prompt_template": "test", "required_input_types": []},
        "position_x": 0,
        "position_y": 0
    }
    node_resp = client.post(f"/api/workflows/{workflow_id}/nodes", json=node_data)
    assert node_resp.status_code == 201
    node_record_id = node_resp.json()["id"]

    run_resp = client.post("/api/runs", json={"project_id": project_id, "workflow_id": workflow_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Создаём первое выполнение
    exec1_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "sup_old",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    assert exec1_resp.status_code == 200
    exec1_id = exec1_resp.json()["id"]

    # Создаём второе выполнение
    exec2_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "sup_new",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    assert exec2_resp.status_code == 200
    exec2_id = exec2_resp.json()["id"]

    # Переводим первое в VALIDATED (прямое обновление БД)
    import asyncpg
    import os
    import asyncio

    async def set_validated():
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            await conn.execute("UPDATE node_executions SET status = 'VALIDATED' WHERE id = $1", exec1_id)
        finally:
            await conn.close()
    asyncio.run(set_validated())

    # Вызываем supersede
    sup_resp = client.post(f"/api/executions/{exec1_id}/supersede?new_execution_id={exec2_id}")
    print(f"Supersede status: {sup_resp.status_code}")
    print(f"Supersede response: {sup_resp.text}")
    assert sup_resp.status_code == 200
    assert sup_resp.json()["status"] == "superseded"

    # Проверяем статус первого
    async def get_status(eid):
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            row = await conn.fetchrow("SELECT status FROM node_executions WHERE id = $1", eid)
            return row["status"]
        finally:
            await conn.close()
    status1 = asyncio.run(get_status(exec1_id))
    assert status1 == "SUPERSEDED"
