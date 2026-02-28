# #ADDED: Fixed mock paths to match actual imports in routers/projects.py
# #ADDED: Added mocks for check_name_exists and transaction context manager

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from server import app
from repositories.project_repository import DEFAULT_OWNER_ID

client = TestClient(app)

def test_get_models():
    """Test that /api/models returns a list."""
    response = client.get("/api/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch("repositories.base.transaction")
@patch("repositories.project_repository.check_name_exists", new_callable=AsyncMock)
@patch("repositories.project_repository.create_project", new_callable=AsyncMock)
@patch("repositories.project_repository.get_projects", new_callable=AsyncMock)
@patch("repositories.project_repository.get_project", new_callable=AsyncMock)
def test_projects_crud(
    mock_get_project,
    mock_get_projects,
    mock_create_project,
    mock_check_name_exists,
    mock_transaction,
):
    """Test project CRUD operations with mocked repository layer."""
    # Setup transaction mock to act as async context manager
    mock_transaction.return_value.__aenter__ = AsyncMock(return_value=None)
    mock_transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Setup mock returns
    mock_check_name_exists.return_value = False  # name is unique
    mock_create_project.return_value = "test-proj-id"

    # Mock get_project called after creation to return full project
    mock_get_project.return_value = {
        "id": "test-proj-id",
        "name": "Test Project",
        "description": "Test",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }

    # Mock get_projects for listing
    mock_get_projects.return_value = [mock_get_project.return_value]

    # Test create
    response = client.post("/api/projects", json={"name": "Test Project", "description": "Test"})
    assert response.status_code == 201  # should be 201 Created
    data = response.json()
    assert data["id"] == "test-proj-id"
    assert data["name"] == "Test Project"

    # #CHANGED: check_name_exists now expects owner_id parameter
    mock_check_name_exists.assert_called_once_with("Test Project", owner_id=DEFAULT_OWNER_ID)
    mock_create_project.assert_called_once()

    # Test list
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["id"] == "test-proj-id"

    # Verify mocks were called as expected
    mock_get_projects.assert_called_once()
    mock_get_project.assert_called()
