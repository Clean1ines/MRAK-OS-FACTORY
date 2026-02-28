# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from server import app
from repositories.project_repository import DEFAULT_OWNER_ID

client = TestClient(app)

def test_get_models():
    """Test that /api/models returns a list."""
    response = client.get("/api/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("routers.projects.db.create_project", new_callable=AsyncMock)
@patch("routers.projects.db.get_projects", new_callable=AsyncMock)
@patch("routers.artifacts.db.get_artifacts", new_callable=AsyncMock)
def test_projects_crud(mock_get_artifacts, mock_get_projects, mock_create_project):
    """Test project CRUD operations with mocked db module."""
    # Setup mocks
    mock_create_project.return_value = "test-proj-id"
    mock_get_projects.return_value = [{
        "id": "test-proj-id", 
        "name": "Test Project", 
        "description": "Test"
    }]
    mock_get_artifacts.return_value = []

    # Test create
    response = client.post("/api/projects", json={"name": "Test Project", "description": "Test"})
    assert response.status_code == 201  # should be 201 Created
    data = response.json()
    assert data["id"] == "test-proj-id"
    assert data["name"] == "Test Project"

    # Test list
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["id"] == "test-proj-id"

    # Test get artifacts
    response = client.get("/api/projects/test-proj-id/artifacts")
    assert response.status_code == 200
    assert response.json() == []