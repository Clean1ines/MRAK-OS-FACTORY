import pytest
from fastapi.testclient import TestClient

def test_create_workflow_api(sync_client: TestClient):
    response = sync_client.post("/api/workflows", json={
        "name": "API WF",
        "description": "Created via API",
        "is_default": True
    })
    assert response.status_code == 200  # вместо 201
    data = response.json()
    assert "id" in data

    wf_id = data["id"]
    list_resp = sync_client.get("/api/workflows")
    assert list_resp.status_code == 200
    workflows = list_resp.json()
    assert any(w["id"] == wf_id for w in workflows)

def test_get_workflow_detail(sync_client: TestClient):
    create_resp = sync_client.post("/api/workflows", json={"name": "Detail WF", "description": ""})
    wf_id = create_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "node1",
        "prompt_key": "02_IDEA_CLARIFIER",
        "config": {},
        "position_x": 10,
        "position_y": 20
    })
    assert node_resp.status_code == 200  # вместо 201
    node_record_id = node_resp.json()["id"]

    detail_resp = sync_client.get(f"/api/workflows/{wf_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["workflow"]["id"] == wf_id
    assert len(detail["nodes"]) == 1
    assert detail["nodes"][0]["node_id"] == "node1"
    assert len(detail["edges"]) == 0

def test_update_workflow_api(sync_client: TestClient):
    create_resp = sync_client.post("/api/workflows", json={"name": "Update WF", "description": "Old"})
    wf_id = create_resp.json()["id"]

    update_resp = sync_client.put(f"/api/workflows/{wf_id}", json={"name": "New Name", "is_default": True})
    assert update_resp.status_code == 200

    get_resp = sync_client.get(f"/api/workflows/{wf_id}")
    wf = get_resp.json()["workflow"]
    assert wf["name"] == "New Name"
    assert wf["is_default"] is True
    assert wf["description"] == "Old"

def test_delete_workflow_api(sync_client: TestClient):
    create_resp = sync_client.post("/api/workflows", json={"name": "To Delete"})
    wf_id = create_resp.json()["id"]

    delete_resp = sync_client.delete(f"/api/workflows/{wf_id}")
    assert delete_resp.status_code == 200

    get_resp = sync_client.get(f"/api/workflows/{wf_id}")
    assert get_resp.status_code == 404

def test_create_node_api(sync_client: TestClient):
    wf_resp = sync_client.post("/api/workflows", json={"name": "Node Test"})
    wf_id = wf_resp.json()["id"]

    node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "n1",
        "prompt_key": "02_IDEA_CLARIFIER",
        "config": {"temp": 0.8},
        "position_x": 1.0,
        "position_y": 2.0
    })
    assert node_resp.status_code == 200  # вместо 201
    node_id = node_resp.json()["id"]

    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    nodes = detail["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["id"] == node_id
    assert nodes[0]["node_id"] == "n1"
    assert nodes[0]["config"] == {"temp": 0.8}

def test_update_node_api(sync_client: TestClient):
    wf_resp = sync_client.post("/api/workflows", json={"name": "Update Node"})
    wf_id = wf_resp.json()["id"]
    node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "n1",
        "prompt_key": "02_IDEA_CLARIFIER",
        "config": {},
        "position_x": 0,
        "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    update_resp = sync_client.put(f"/api/workflows/nodes/{node_record_id}", json={
        "prompt_key": "03_PRODUCT_COUNCIL",
        "config": {"new": True},
        "position_x": 100
    })
    assert update_resp.status_code == 200

    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    node = detail["nodes"][0]
    assert node["prompt_key"] == "03_PRODUCT_COUNCIL"
    assert node["config"] == {"new": True}
    assert node["position_x"] == 100
    assert node["position_y"] == 0

def test_delete_node_api(sync_client: TestClient):
    wf_resp = sync_client.post("/api/workflows", json={"name": "Delete Node"})
    wf_id = wf_resp.json()["id"]
    node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
        "node_id": "n1",
        "prompt_key": "02_IDEA_CLARIFIER",
        "config": {},
        "position_x": 0,
        "position_y": 0
    })
    node_record_id = node_resp.json()["id"]

    delete_resp = sync_client.delete(f"/api/workflows/nodes/{node_record_id}")
    assert delete_resp.status_code == 200

    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    assert len(detail["nodes"]) == 0

def test_create_edge_api(sync_client: TestClient):
    wf_resp = sync_client.post("/api/workflows", json={"name": "Edge Test"})
    wf_id = wf_resp.json()["id"]
    sync_client.post(f"/api/workflows/{wf_id}/nodes", json={"node_id": "a", "prompt_key": "02", "config": {}, "position_x": 0, "position_y": 0})
    sync_client.post(f"/api/workflows/{wf_id}/nodes", json={"node_id": "b", "prompt_key": "03", "config": {}, "position_x": 100, "position_y": 0})

    edge_resp = sync_client.post(f"/api/workflows/{wf_id}/edges", json={
        "source_node": "a",
        "target_node": "b",
        "source_output": "out",
        "target_input": "in"
    })
    assert edge_resp.status_code == 200  # вместо 201
    edge_id = edge_resp.json()["id"]

    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    assert len(detail["edges"]) == 1
    assert detail["edges"][0]["id"] == edge_id

def test_delete_edge_api(sync_client: TestClient):
    wf_resp = sync_client.post("/api/workflows", json={"name": "Delete Edge"})
    wf_id = wf_resp.json()["id"]
    sync_client.post(f"/api/workflows/{wf_id}/nodes", json={"node_id": "a", "prompt_key": "02", "config": {}, "position_x": 0, "position_y": 0})
    sync_client.post(f"/api/workflows/{wf_id}/nodes", json={"node_id": "b", "prompt_key": "03", "config": {}, "position_x": 100, "position_y": 0})
    edge_resp = sync_client.post(f"/api/workflows/{wf_id}/edges", json={"source_node": "a", "target_node": "b"})
    edge_id = edge_resp.json()["id"]

    delete_resp = sync_client.delete(f"/api/workflows/edges/{edge_id}")
    assert delete_resp.status_code == 200

    detail = sync_client.get(f"/api/workflows/{wf_id}").json()
    assert len(detail["edges"]) == 0