"""
Debug version of runs tests with unique project names to avoid 400 errors.
Все вызовы execute_node используют record_id узла (UUID), а не логическое имя.
Исправлено: при ручном переводе в COMPLETED или VALIDATED создаётся артефакт и заполняется output_artifact_id.
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

    # Вручную создаём артефакт и переводим выполнение в COMPLETED
    import asyncpg
    import os
    import asyncio

    async def prepare():
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            # Создаём артефакт
            artifact_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO artifacts (id, project_id, type, content, owner, status)
                VALUES ($1, $2, 'test', '{"result": "ok"}', 'system', 'ACTIVE')
            """, artifact_id, project_id)
            # Обновляем выполнение: статус COMPLETED и output_artifact_id
            await conn.execute("""
                UPDATE node_executions
                SET status = 'COMPLETED', output_artifact_id = $1
                WHERE id = $2
            """, artifact_id, exec_id)
        finally:
            await conn.close()
    asyncio.run(prepare())

    # Валидируем
    validate_resp = client.post(f"/api/executions/{exec_id}/validate")
    print(f"Validate status: {validate_resp.status_code}")
    print(f"Validate response: {validate_resp.text}")
    assert validate_resp.status_code == 200
    data = validate_resp.json()
    assert data["id"] == exec_id
    assert data["status"] == "VALIDATED"

# === NEW TESTS FOR ADR-010 ===

def test_freeze_run_success():
    """Создаём run и замораживаем его (новый формат ответа)."""
    print("\n=== test_freeze_run_success (updated) ===")
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
    data = freeze_resp.json()
    assert data["id"] == run_id
    assert data["status"] == "FROZEN"
    assert data["frozen_at"] is not None
    assert data["archived_at"] is None

def test_freeze_already_frozen_run_fails():
    """Попытка заморозить уже замороженный run."""
    print("\n=== test_freeze_already_frozen_run_fails ===")
    proj_name = unique_name("Freeze Twice Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Freeze Twice WF")
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

    # Замораживаем первый раз
    freeze1 = client.post(f"/api/runs/{run_id}/freeze")
    assert freeze1.status_code == 200

    # Второй раз
    freeze2 = client.post(f"/api/runs/{run_id}/freeze")
    print(f"Second freeze status: {freeze2.status_code}")
    print(f"Second freeze response: {freeze2.text}")
    assert freeze2.status_code == 409
    assert "Cannot freeze run with status FROZEN" in freeze2.text

def test_archive_run_success():
    """Создаём run, замораживаем, затем архивируем."""
    print("\n=== test_archive_run_success ===")
    proj_name = unique_name("Archive Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Archive WF")
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

    # Замораживаем
    freeze_resp = client.post(f"/api/runs/{run_id}/freeze")
    assert freeze_resp.status_code == 200

    # Архивируем
    archive_resp = client.post(f"/api/runs/{run_id}/archive")
    print(f"Archive status: {archive_resp.status_code}")
    print(f"Archive response: {archive_resp.text}")
    assert archive_resp.status_code == 200
    data = archive_resp.json()
    assert data["id"] == run_id
    assert data["status"] == "ARCHIVED"
    assert data["archived_at"] is not None

def test_archive_open_run_fails():
    """Попытка архивировать run в статусе OPEN (без заморозки)."""
    print("\n=== test_archive_open_run_fails ===")
    proj_name = unique_name("Archive Open Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Archive Open WF")
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

    archive_resp = client.post(f"/api/runs/{run_id}/archive")
    print(f"Archive open run status: {archive_resp.status_code}")
    print(f"Archive open run response: {archive_resp.text}")
    assert archive_resp.status_code == 409
    assert "Cannot archive run with status OPEN" in archive_resp.text

def test_execute_node_in_frozen_run_fails():
    """Попытка выполнить узел в замороженном run."""
    print("\n=== test_execute_node_in_frozen_run_fails ===")
    proj_name = unique_name("Exec Frozen Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Exec Frozen WF")
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

    # Замораживаем run
    freeze_resp = client.post(f"/api/runs/{run_id}/freeze")
    assert freeze_resp.status_code == 200

    # Пытаемся выполнить узел
    exec_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "fail_key",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    print(f"Execute in frozen run status: {exec_resp.status_code}")
    print(f"Execute in frozen run response: {exec_resp.text}")
    assert exec_resp.status_code == 400
    assert "not OPEN" in exec_resp.text

def test_validate_in_frozen_run_fails():
    """Попытка валидировать выполнение в замороженном run."""
    print("\n=== test_validate_in_frozen_run_fails ===")
    proj_name = unique_name("Validate Frozen Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Validate Frozen WF")
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
        "idempotency_key": "val_frozen",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    assert exec_resp.status_code == 200
    exec_id = exec_resp.json()["id"]

    # Переводим выполнение в COMPLETED (через прямые SQL-запросы)
    import asyncpg
    import os
    import asyncio

    async def prepare_completed():
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            # Создаём артефакт
            artifact_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO artifacts (id, project_id, type, content, owner, status)
                VALUES ($1, $2, 'test', '{"result": "ok"}', 'system', 'ACTIVE')
            """, artifact_id, project_id)
            # Обновляем выполнение
            await conn.execute("""
                UPDATE node_executions
                SET status = 'COMPLETED', output_artifact_id = $1
                WHERE id = $2
            """, artifact_id, exec_id)
        finally:
            await conn.close()
    asyncio.run(prepare_completed())

    # Замораживаем run
    freeze_resp = client.post(f"/api/runs/{run_id}/freeze")
    assert freeze_resp.status_code == 200

    # Пытаемся валидировать
    validate_resp = client.post(f"/api/executions/{exec_id}/validate")
    print(f"Validate in frozen run status: {validate_resp.status_code}")
    print(f"Validate in frozen run response: {validate_resp.text}")
    assert validate_resp.status_code == 409
    assert "Run is not OPEN" in validate_resp.text

def test_supersede_in_frozen_run_fails():
    """Попытка заместить выполнение в замороженном run."""
    print("\n=== test_supersede_in_frozen_run_fails ===")
    proj_name = unique_name("Supersede Frozen Project")
    proj_resp = client.post("/api/projects", json={"name": proj_name, "description": ""})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    wf_name = unique_name("Supersede Frozen WF")
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

    # Создаём два выполнения
    exec1_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "sup1",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    assert exec1_resp.status_code == 200
    exec1_id = exec1_resp.json()["id"]

    exec2_resp = client.post(f"/api/runs/{run_id}/nodes/{node_record_id}/execute", json={
        "idempotency_key": "sup2",
        "parent_execution_id": None,
        "input_artifact_ids": []
    })
    assert exec2_resp.status_code == 200
    exec2_id = exec2_resp.json()["id"]

    # Переводим первое выполнение в VALIDATED (прямые SQL)
    import asyncpg
    import os
    import asyncio

    async def prepare_validated():
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            artifact_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO artifacts (id, project_id, type, content, owner, status)
                VALUES ($1, $2, 'test', '{"result": "old"}', 'system', 'ACTIVE')
            """, artifact_id, project_id)
            await conn.execute("""
                UPDATE node_executions
                SET status = 'VALIDATED', output_artifact_id = $1
                WHERE id = $2
            """, artifact_id, exec1_id)
        finally:
            await conn.close()
    asyncio.run(prepare_validated())

    # Замораживаем run
    freeze_resp = client.post(f"/api/runs/{run_id}/freeze")
    assert freeze_resp.status_code == 200

    # Пытаемся заместить
    sup_resp = client.post(f"/api/executions/{exec1_id}/supersede?new_execution_id={exec2_id}")
    print(f"Supersede in frozen run status: {sup_resp.status_code}")
    print(f"Supersede in frozen run response: {sup_resp.text}")
    assert sup_resp.status_code == 409
    assert "Run is not OPEN" in sup_resp.text