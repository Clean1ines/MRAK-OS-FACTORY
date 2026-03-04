"""
Integration tests for artifacts router.
Uses real database, mocks only external LLM via groq_client.
All data is created via API to ensure visibility across connections.
"""
import pytest
import uuid
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from server import app
from dependencies import get_artifact_service
from artifact_service import ArtifactService
from use_cases.save_artifact_package import SaveArtifactPackageUseCase

def unique_name(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def mock_groq_client(mocker):
    mock = MagicMock()
    mock.create_completion = MagicMock()
    # Default success response
    mock.create_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"result": "ok"}'))]
    )
    return mock

@pytest.fixture(autouse=True)
def override_groq_client(mock_groq_client, mocker):
    from dependencies import get_artifact_service
    real_service = get_artifact_service()
    mocker.patch.object(real_service, 'groq_client', mock_groq_client)
    yield

@pytest.fixture
def mock_save_package_use_case(mocker):
    mock = AsyncMock(return_value={"id": str(uuid.uuid4()), "duplicate": False})
    mocker.patch('routers.artifacts.SaveArtifactPackageUseCase', return_value=AsyncMock(execute=mock))
    return mock

# ----------------------------------------------------------------------
def test_list_artifacts_empty(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("EmptyProj")})
    assert proj_resp.status_code == 201, f"Failed to create project: {proj_resp.text}"
    proj_id = proj_resp.json()["id"]
    response = sync_client.get(f"/api/projects/{proj_id}/artifacts")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json() == []

def test_list_artifacts_with_type_filter(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("FilterProj")})
    assert proj_resp.status_code == 201, f"Failed to create project: {proj_resp.text}"
    proj_id = proj_resp.json()["id"]

    art1 = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "typeA",
        "content": "content A",
        "generate": False
    })
    art2 = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "typeB",
        "content": "content B",
        "generate": False
    })
    assert art1.status_code == 200, f"Failed to create artifact typeA: {art1.text}"
    assert art2.status_code == 200, f"Failed to create artifact typeB: {art2.text}"

    resp_all = sync_client.get(f"/api/projects/{proj_id}/artifacts")
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert len(data_all) == 2, f"Expected 2 artifacts, got {len(data_all)}"

    resp_a = sync_client.get(f"/api/projects/{proj_id}/artifacts", params={"type": "typeA"})
    assert resp_a.status_code == 200
    data = resp_a.json()
    assert len(data) == 1
    assert data[0]["type"] == "typeA"

def test_create_artifact_draft_success(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("DraftProj")})
    assert proj_resp.status_code == 201, f"Failed to create project: {proj_resp.text}"
    proj_id = proj_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "artifact_type": "test_draft",
        "content": "some text",
        "generate": False
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "id" in data, f"Response missing 'id': {data}"
    assert data["generated"] is False

    list_resp = sync_client.get(f"/api/projects/{proj_id}/artifacts")
    assert list_resp.status_code == 200
    artifacts = list_resp.json()
    assert any(a["id"] == data["id"] for a in artifacts)

def test_create_artifact_draft_with_parent(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("ParentProj")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    parent_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "parent",
        "content": "parent content",
        "generate": False
    })
    assert parent_resp.status_code == 200, f"Failed to create parent: {parent_resp.text}"
    parent_id = parent_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "artifact_type": "child",
        "content": "child content",
        "parent_id": parent_id,
        "generate": False
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "id" in data
    assert data["generated"] is False

def test_create_artifact_generated_no_parent(sync_client, mock_groq_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("GenNoParent")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "artifact_type": "generated",
        "content": "user input",
        "generate": True,
        "model": "test-model"
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "id" in data
    assert data["generated"] is True
    mock_groq_client.create_completion.assert_called_once()

def test_create_artifact_generated_with_parent(sync_client, mock_groq_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("GenParent")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    parent_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "parent",
        "content": "parent data",
        "generate": False
    })
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "artifact_type": "child",
        "content": "feedback",
        "parent_id": parent_id,
        "generate": True
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "id" in data
    mock_groq_client.create_completion.assert_called_once()

def test_create_artifact_generated_parent_not_found(sync_client, mock_groq_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("ParentNotFound")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    fake_parent = str(uuid.uuid4())
    payload = {
        "project_id": proj_id,
        "artifact_type": "child",
        "content": "feedback",
        "parent_id": fake_parent,
        "generate": True
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    assert "Parent artifact not found" in response.json()["error"]
    mock_groq_client.create_completion.assert_not_called()

def test_create_artifact_generated_validation_error(sync_client, mock_groq_client):
    mock_groq_client.create_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='invalid'))]
    )
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("ValError")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "artifact_type": "BusinessRequirementPackage",
        "content": "input",
        "generate": True
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    err_msg = response.json()["error"].lower()
    assert "validation error" in err_msg or "failed to generate" in err_msg

def test_create_artifact_generated_other_error(sync_client, mock_groq_client):
    mock_groq_client.create_completion.side_effect = Exception("LLM crash")
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("OtherError")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "artifact_type": "generated",
        "content": "input",
        "generate": True
    }
    response = sync_client.post("/api/artifact", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    err_msg = response.json()["error"].lower()
    assert "failed to generate" in err_msg

def test_latest_artifact_found(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Latest")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    parent_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "parent",
        "content": "parent",
        "generate": False
    })
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["id"]

    child_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "child",
        "content": "v1",
        "parent_id": parent_id,
        "generate": False
    })
    assert child_resp.status_code == 200
    child_id = child_resp.json()["id"]

    response = sync_client.get("/api/latest_artifact", params={"parent_id": parent_id, "type": "child"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["exists"] is True
    assert data["artifact_id"] == child_id
    assert data["content"] == {"text": "v1"}

def test_latest_artifact_not_found(sync_client):
    fake_parent = str(uuid.uuid4())
    response = sync_client.get("/api/latest_artifact", params={"parent_id": fake_parent, "type": "none"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["exists"] is False

def test_validate_artifact_success(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Validate")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    art_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "test",
        "content": "data",
        "generate": False
    })
    assert art_resp.status_code == 200
    art_id = art_resp.json()["id"]

    payload = {"artifact_id": art_id, "status": "ACTIVE"}
    response = sync_client.post("/api/validate_artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["status"] == "updated"

def test_validate_artifact_db_error(sync_client, mocker):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("ValidateErr")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    art_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "test",
        "content": "data",
        "generate": False
    })
    assert art_resp.status_code == 200
    art_id = art_resp.json()["id"]

    mocker.patch('db.update_artifact_status', side_effect=Exception("DB down"))
    payload = {"artifact_id": art_id, "status": "ACTIVE"}
    response = sync_client.post("/api/validate_artifact", json=payload)
    assert response.status_code == 500, f"Expected 500, got {response.status_code}: {response.text}"
    assert "DB down" in response.json()["error"]

def test_delete_artifact_success(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Delete")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    art_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "test",
        "content": "data",
        "generate": False
    })
    assert art_resp.status_code == 200
    art_id = art_resp.json()["id"]

    delete_resp = sync_client.delete(f"/api/artifact/{art_id}")
    assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"
    assert delete_resp.json()["status"] == "deleted"

    list_resp = sync_client.get(f"/api/projects/{proj_id}/artifacts")
    assert list_resp.status_code == 200
    assert not any(a["id"] == art_id for a in list_resp.json())

def test_delete_artifact_not_found(sync_client):
    fake_id = str(uuid.uuid4())
    response = sync_client.delete(f"/api/artifact/{fake_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["status"] == "deleted"

def test_delete_artifact_db_error(sync_client, mocker):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("DeleteErr")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    art_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "test",
        "content": "data",
        "generate": False
    })
    assert art_resp.status_code == 200
    art_id = art_resp.json()["id"]

    mocker.patch('db.delete_artifact', side_effect=Exception("DB down"))
    response = sync_client.delete(f"/api/artifact/{art_id}")
    assert response.status_code == 500, f"Expected 500, got {response.status_code}: {response.text}"
    assert "DB down" in response.json()["error"]

def test_generate_artifact_endpoint_success(sync_client, mock_groq_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("GenEndpoint")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    payload = {
        "artifact_type": "gen_type",
        "feedback": "user feedback",
        "model": "model-x",
        "project_id": proj_id
    }
    response = sync_client.post("/api/generate_artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "result" in data
    assert data["result"] == {"result": "ok"}
    mock_groq_client.create_completion.assert_called_once()

def test_generate_artifact_with_parent(sync_client, mock_groq_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("GenParent")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    parent_resp = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "parent",
        "content": "p",
        "generate": False
    })
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["id"]

    payload = {
        "artifact_type": "child",
        "parent_id": parent_id,
        "feedback": "fb",
        "model": "m",
        "project_id": proj_id
    }
    response = sync_client.post("/api/generate_artifact", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["result"] == {"result": "ok"}
    mock_groq_client.create_completion.assert_called_once()

def test_generate_artifact_validation_error(sync_client, mock_groq_client):
    mock_groq_client.create_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='invalid'))]
    )
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("GenValErr")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    payload = {
        "artifact_type": "BusinessRequirementPackage",
        "feedback": "",
        "model": "m",
        "project_id": proj_id
    }
    response = sync_client.post("/api/generate_artifact", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    err_msg = response.json()["error"].lower()
    assert "validation error" in err_msg or "failed to generate" in err_msg

def test_save_artifact_package_success(sync_client, mock_save_package_use_case):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Package")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    payload = {
        "project_id": proj_id,
        "parent_id": str(uuid.uuid4()),
        "artifact_type": "package",
        "content": [{"some": "data"}]
    }
    response = sync_client.post("/api/save_artifact_package", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "id" in data
    assert data["duplicate"] is False
    mock_save_package_use_case.assert_awaited_once()
    call_args = mock_save_package_use_case.call_args[0][0]
    assert call_args.project_id == proj_id
    assert call_args.artifact_type == "package"

def test_save_artifact_package_error(sync_client, mock_save_package_use_case):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("PackageErr")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    mock_save_package_use_case.side_effect = Exception("use case error")
    payload = {
        "project_id": proj_id,
        "parent_id": str(uuid.uuid4()),
        "artifact_type": "package",
        "content": []
    }
    response = sync_client.post("/api/save_artifact_package", json=payload)
    assert response.status_code == 500, f"Expected 500, got {response.status_code}: {response.text}"
    assert "use case error" in response.json()["error"]

def test_get_project_messages(sync_client):
    proj_resp = sync_client.post("/api/projects", json={"name": unique_name("Messages")})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    resp1 = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "LLMResponse",
        "content": "msg1",
        "generate": False
    })
    resp2 = sync_client.post("/api/artifact", json={
        "project_id": proj_id,
        "artifact_type": "LLMResponse",
        "content": "msg2",
        "generate": False
    })
    assert resp1.status_code == 200, f"Failed to create msg1: {resp1.text}"
    assert resp2.status_code == 200, f"Failed to create msg2: {resp2.text}"

    response = sync_client.get(f"/api/projects/{proj_id}/messages")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert len(data) == 2
    times = [item["created_at"] for item in data]
    assert times == sorted(times)

def test_list_artifact_types_empty(sync_client):
    response = sync_client.get("/api/artifact-types")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_artifact_type_success(sync_client):
    type_name = unique_name("MyType")
    payload = {
        "type": type_name,
        "schema": {"fields": ["name"]},
        "allowed_parents": ["ParentType"],
        "requires_clarification": True,
        "icon": "📄"
    }
    response = sync_client.post("/api/artifact-types", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    assert response.json()["type"] == type_name

    get_resp = sync_client.get(f"/api/artifact-types/{type_name}")
    assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
    data = get_resp.json()
    assert data["type"] == type_name
    assert data["schema"] == {"fields": ["name"]}
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)

def test_create_artifact_type_missing_field(sync_client):
    payload = {"type": "Incomplete"}
    response = sync_client.post("/api/artifact-types", json=payload)
    assert response.status_code == 400
    assert "Missing field" in response.json()["error"]

def test_create_artifact_type_duplicate(sync_client):
    type_name = unique_name("DuplicateType")
    payload = {
        "type": type_name,
        "schema": {"a": 1}
    }
    sync_client.post("/api/artifact-types", json=payload)
    response = sync_client.post("/api/artifact-types", json=payload)
    assert response.status_code == 500
    assert "duplicate key" in response.json()["error"].lower()

def test_get_artifact_type_not_found(sync_client):
    response = sync_client.get("/api/artifact-types/NonExistent")
    assert response.status_code == 404
    assert "Type not found" in response.json()["error"]

def test_update_artifact_type_success(sync_client):
    type_name = unique_name("Updatable")
    payload = {
        "type": type_name,
        "schema": {"v": 1}
    }
    sync_client.post("/api/artifact-types", json=payload)

    update = {
        "schema": {"v": 2},
        "icon": "new-icon"
    }
    response = sync_client.put(f"/api/artifact-types/{type_name}", json=update)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["status"] == "updated"

    get_resp = sync_client.get(f"/api/artifact-types/{type_name}")
    assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
    data = get_resp.json()
    assert data["schema"] == {"v": 2}
    assert data["icon"] == "new-icon"

def test_update_artifact_type_not_found(sync_client):
    response = sync_client.put("/api/artifact-types/NonExistent", json={"schema": {}})
    assert response.status_code == 404

def test_delete_artifact_type_success(sync_client):
    type_name = unique_name("ToDelete")
    payload = {"type": type_name, "schema": {}}
    sync_client.post("/api/artifact-types", json=payload)

    response = sync_client.delete(f"/api/artifact-types/{type_name}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["status"] == "deleted"

    get_resp = sync_client.get(f"/api/artifact-types/{type_name}")
    assert get_resp.status_code == 404

def test_delete_artifact_type_not_found(sync_client):
    response = sync_client.delete("/api/artifact-types/NonExistent")
    assert response.status_code == 404
