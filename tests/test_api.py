# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from server import app

client = TestClient(app)

def test_get_models():
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
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-proj-id"

    # Test list
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert any(p["id"] == "test-proj-id" for p in projects)

    # Test get artifacts
    response = client.get("/api/projects/test-proj-id/artifacts")
    assert response.status_code == 200
    assert response.json() == []