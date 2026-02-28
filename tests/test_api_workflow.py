import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_create_workflow_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create, \
         patch("db.list_workflows", new_callable=AsyncMock) as mock_list:

        mock_create.return_value = "test-wf-id"
        mock_list.return_value = []

        response = sync_client.post("/api/workflows", json={
            "name": "API WF",
            "description": "Created via API",
            "is_default": True
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

        wf_id = data["id"]
        mock_list.return_value = [{"id": wf_id, "name": "API WF", "description": "Created via API", "is_default": True}]
        list_resp = sync_client.get("/api/workflows")
        assert list_resp.status_code == 200
        workflows = list_resp.json()
        assert any(w["id"] == wf_id for w in workflows)

def test_get_workflow_detail(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get_wf, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_nodes, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_edges, \
         patch("db.create_workflow_node", new_callable=AsyncMock) as mock_create_node:

        mock_create.return_value = "wf-id"
        mock_get_wf.return_value = {"id": "wf-id", "name": "Detail WF", "description": ""}
        mock_nodes.return_value = []
        mock_edges.return_value = []
        mock_create_node.return_value = "node-record-id"

        create_resp = sync_client.post("/api/workflows", json={"name": "Detail WF", "description": ""})
        wf_id = create_resp.json()["id"]

        node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
            "node_id": "node1",
            "prompt_key": "02_IDEA_CLARIFIER",
            "config": {},
            "position_x": 10,
            "position_y": 20
        })
        assert node_resp.status_code == 200
        node_record_id = node_resp.json()["id"]

        mock_nodes.return_value = [{"id": node_record_id, "node_id": "node1", "prompt_key": "02_IDEA_CLARIFIER", "config": {}, "position_x": 10, "position_y": 20}]
        detail_resp = sync_client.get(f"/api/workflows/{wf_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["workflow"]["id"] == wf_id
        assert len(detail["nodes"]) == 1
        assert detail["nodes"][0]["node_id"] == "node1"
        assert len(detail["edges"]) == 0

def test_update_workflow_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get, \
         patch("db.update_workflow", new_callable=AsyncMock) as mock_update, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_nodes, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_edges:

        mock_create.return_value = "wf-id"
        mock_get.return_value = {"id": "wf-id", "name": "Update WF", "description": "Old"}
        mock_nodes.return_value = []
        mock_edges.return_value = []

        create_resp = sync_client.post("/api/workflows", json={"name": "Update WF", "description": "Old"})
        wf_id = create_resp.json()["id"]

        update_resp = sync_client.put(f"/api/workflows/{wf_id}", json={"name": "New Name", "is_default": True})
        assert update_resp.status_code == 200

        mock_get.return_value = {"id": wf_id, "name": "New Name", "description": "Old", "is_default": True}
        get_resp = sync_client.get(f"/api/workflows/{wf_id}")
        assert get_resp.status_code == 200
        wf = get_resp.json()["workflow"]
        assert wf["name"] == "New Name"
        assert wf["is_default"] is True
        assert wf["description"] == "Old"

def test_delete_workflow_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get, \
         patch("db.delete_workflow", new_callable=AsyncMock) as mock_delete:

        mock_create.return_value = "wf-id"
        mock_get.side_effect = [{"id": "wf-id"}, None]

        create_resp = sync_client.post("/api/workflows", json={"name": "To Delete"})
        wf_id = create_resp.json()["id"]

        delete_resp = sync_client.delete(f"/api/workflows/{wf_id}")
        assert delete_resp.status_code == 200

        get_resp = sync_client.get(f"/api/workflows/{wf_id}")
        assert get_resp.status_code == 404

def test_create_node_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create_wf, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get_wf, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_get_nodes, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_get_edges, \
         patch("db.create_workflow_node", new_callable=AsyncMock) as mock_create_node:

        mock_create_wf.return_value = "wf-id"
        mock_get_wf.return_value = {"id": "wf-id", "name": "Node Test"}
        mock_get_nodes.return_value = []
        mock_get_edges.return_value = []
        mock_create_node.return_value = "node-record-id"

        wf_resp = sync_client.post("/api/workflows", json={"name": "Node Test"})
        wf_id = wf_resp.json()["id"]

        node_resp = sync_client.post(f"/api/workflows/{wf_id}/nodes", json={
            "node_id": "n1",
            "prompt_key": "02_IDEA_CLARIFIER",
            "config": {"temp": 0.8},
            "position_x": 1.0,
            "position_y": 2.0
        })
        assert node_resp.status_code == 200
        node_id = node_resp.json()["id"]

        mock_get_nodes.return_value = [{"id": node_id, "node_id": "n1", "prompt_key": "02_IDEA_CLARIFIER", "config": {"temp": 0.8}, "position_x": 1.0, "position_y": 2.0}]
        mock_get_edges.return_value = []
        detail = sync_client.get(f"/api/workflows/{wf_id}").json()
        nodes = detail["nodes"]
        assert len(nodes) == 1
        assert nodes[0]["id"] == node_id
        assert nodes[0]["node_id"] == "n1"
        assert nodes[0]["config"] == {"temp": 0.8}

def test_update_node_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create_wf, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get_wf, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_get_nodes, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_get_edges, \
         patch("db.create_workflow_node", new_callable=AsyncMock) as mock_create_node, \
         patch("db.update_workflow_node", new_callable=AsyncMock) as mock_update_node:

        mock_create_wf.return_value = "wf-id"
        mock_get_wf.return_value = {"id": "wf-id", "name": "Update Node"}
        mock_get_nodes.return_value = []
        mock_get_edges.return_value = []
        mock_create_node.return_value = "node-record-id"

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

        mock_get_nodes.return_value = [{"id": node_record_id, "node_id": "n1", "prompt_key": "03_PRODUCT_COUNCIL", "config": {"new": True}, "position_x": 100, "position_y": 0}]
        mock_get_edges.return_value = []
        detail = sync_client.get(f"/api/workflows/{wf_id}").json()
        node = detail["nodes"][0]
        assert node["prompt_key"] == "03_PRODUCT_COUNCIL"
        assert node["config"] == {"new": True}
        assert node["position_x"] == 100
        assert node["position_y"] == 0

def test_delete_node_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create_wf, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get_wf, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_get_nodes, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_get_edges, \
         patch("db.create_workflow_node", new_callable=AsyncMock) as mock_create_node, \
         patch("db.delete_workflow_node", new_callable=AsyncMock) as mock_delete_node:

        mock_create_wf.return_value = "wf-id"
        mock_get_wf.return_value = {"id": "wf-id", "name": "Delete Node"}
        mock_get_nodes.return_value = []
        mock_get_edges.return_value = []
        mock_create_node.return_value = "node-record-id"

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

        mock_get_nodes.return_value = []
        detail = sync_client.get(f"/api/workflows/{wf_id}").json()
        assert len(detail["nodes"]) == 0

def test_create_edge_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create_wf, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get_wf, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_get_nodes, \
         patch("db.create_workflow_node", new_callable=AsyncMock) as mock_create_node, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_get_edges, \
         patch("db.create_workflow_edge", new_callable=AsyncMock) as mock_create_edge:

        mock_create_wf.return_value = "wf-id"
        mock_get_wf.return_value = {"id": "wf-id", "name": "Edge Test"}
        mock_create_node.side_effect = ["node-a-id", "node-b-id"]
        mock_get_nodes.return_value = [
            {"node_id": "a"}, {"node_id": "b"}
        ]
        mock_create_edge.return_value = "edge-id"

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
        assert edge_resp.status_code == 200
        edge_id = edge_resp.json()["id"]

        mock_get_edges.return_value = [{"id": edge_id, "source_node": "a", "target_node": "b"}]
        detail = sync_client.get(f"/api/workflows/{wf_id}").json()
        assert len(detail["edges"]) == 1
        assert detail["edges"][0]["id"] == edge_id

def test_delete_edge_api(sync_client: TestClient):
    with patch("db.create_workflow", new_callable=AsyncMock) as mock_create_wf, \
         patch("db.get_workflow", new_callable=AsyncMock) as mock_get_wf, \
         patch("db.get_workflow_nodes", new_callable=AsyncMock) as mock_get_nodes, \
         patch("db.create_workflow_node", new_callable=AsyncMock) as mock_create_node, \
         patch("db.create_workflow_edge", new_callable=AsyncMock) as mock_create_edge, \
         patch("db.get_workflow_edges", new_callable=AsyncMock) as mock_get_edges, \
         patch("db.delete_workflow_edge", new_callable=AsyncMock) as mock_delete_edge:

        mock_create_wf.return_value = "wf-id"
        mock_get_wf.return_value = {"id": "wf-id", "name": "Delete Edge"}
        mock_create_node.side_effect = ["node-a-id", "node-b-id"]
        mock_get_nodes.return_value = [{"node_id": "a"}, {"node_id": "b"}]
        mock_create_edge.return_value = "edge-id"
        mock_get_edges.return_value = [{"id": "edge-id"}]

        wf_resp = sync_client.post("/api/workflows", json={"name": "Delete Edge"})
        wf_id = wf_resp.json()["id"]
        sync_client.post(f"/api/workflows/{wf_id}/nodes", json={"node_id": "a", "prompt_key": "02", "config": {}, "position_x": 0, "position_y": 0})
        sync_client.post(f"/api/workflows/{wf_id}/nodes", json={"node_id": "b", "prompt_key": "03", "config": {}, "position_x": 100, "position_y": 0})
        edge_resp = sync_client.post(f"/api/workflows/{wf_id}/edges", json={"source_node": "a", "target_node": "b"})
        edge_id = edge_resp.json()["id"]

        delete_resp = sync_client.delete(f"/api/workflows/edges/{edge_id}")
        assert delete_resp.status_code == 200

        mock_get_edges.return_value = []
        detail = sync_client.get(f"/api/workflows/{wf_id}").json()
        assert len(detail["edges"]) == 0
