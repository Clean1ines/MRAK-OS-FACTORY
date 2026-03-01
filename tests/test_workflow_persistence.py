import pytest
from fastapi.testclient import TestClient
import uuid

def test_create_node_persistence(sync_client: TestClient):
    """Создание узла через POST /workflows/{id}/nodes и проверка сохранения"""
    # Создаём проект
    project_resp = sync_client.post("/api/projects", json={
        "name": f"Test Project {uuid.uuid4()}",
        "description": "For node persistence test"
    })
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    # Создаём воркфлоу
    wf_resp = sync_client.post("/api/workflows", json={
        "name": "Node Persistence Test",
        "project_id": project_id
    })
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    # Создаём узел
    node_data = {
        "node_id": "test-node-1",
        "prompt_key": "TEST_PROMPT",
        "config": {"custom_prompt": "Hello"},
        "position_x": 100,
        "position_y": 200
    }
    node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json=node_data)
    assert node_resp.status_code == 201
    node_record_id = node_resp.json()["id"]

    # Получаем детали воркфлоу и проверяем наличие узла
    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    nodes = detail["nodes"]
    assert len(nodes) == 1
    node = nodes[0]
    assert node["id"] == node_record_id
    assert node["node_id"] == "test-node-1"
    assert node["prompt_key"] == "TEST_PROMPT"
    assert node["config"] == {"custom_prompt": "Hello"}
    assert node["position_x"] == 100
    assert node["position_y"] == 200

def test_create_edge_persistence(sync_client: TestClient):
    """Создание ребра через POST /workflows/{id}/edges и проверка сохранения"""
    project_resp = sync_client.post("/api/projects", json={
        "name": f"Test Project {uuid.uuid4()}",
        "description": "For edge persistence test"
    })
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": "Edge Persistence Test",
        "project_id": project_id
    })
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    # Создаём два узла
    node1 = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "a",
        "prompt_key": "A",
        "config": {},
        "position_x": 0,
        "position_y": 0
    }).json()
    node2 = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "b",
        "prompt_key": "B",
        "config": {},
        "position_x": 100,
        "position_y": 0
    }).json()

    # Создаём ребро
    edge_resp = sync_client.post(f"/api/workflows/{wf_id}/edges", json={
        "source_node": "a",
        "target_node": "b"
    })
    assert edge_resp.status_code == 201
    edge_id = edge_resp.json()["id"]

    # Проверяем в деталях
    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    edges = detail["edges"]
    assert len(edges) == 1
    edge = edges[0]
    assert edge["id"] == edge_id
    assert edge["source_node"] == "a"
    assert edge["target_node"] == "b"

def test_cascade_delete_on_node_removal(sync_client: TestClient):
    """При удалении узла связанные рёбра должны удаляться каскадно"""
    project_resp = sync_client.post("/api/projects", json={
        "name": f"Test Project {uuid.uuid4()}",
        "description": "For cascade test"
    })
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    wf_resp = sync_client.post("/api/workflows", json={
        "name": "Cascade Test",
        "project_id": project_id
    })
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    # Создаём узлы a и b
    node_a = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "a",
        "prompt_key": "A",
        "config": {},
        "position_x": 0,
        "position_y": 0
    }).json()
    node_b = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "b",
        "prompt_key": "B",
        "config": {},
        "position_x": 100,
        "position_y": 0
    }).json()

    # Создаём ребро a -> b
    edge_resp = sync_client.post(f"/api/workflows/{wf_id}/edges", json={
        "source_node": "a",
        "target_node": "b"
    })
    assert edge_resp.status_code == 201
    edge_id = edge_resp.json()["id"]

    # Удаляем узел a
    del_resp = sync_client.delete(f"/api/workflows/nodes/{node_a['id']}")
    assert del_resp.status_code == 200

    # Проверяем, что рёбра исчезли
    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    assert len(detail["edges"]) == 0
    assert len(detail["nodes"]) == 1  # остался только узел b
