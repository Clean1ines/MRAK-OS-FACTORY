import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from server import app
import db  # импортируем db для моков

client = TestClient(app)

def test_get_models():
    response = client.get("/api/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("db.get_projects")
@patch("db.create_project")
@patch("db.get_artifacts")
def test_projects_crud(mock_get_artifacts, mock_create_project, mock_get_projects):
    # Мокаем create_project
    mock_create_project.return_value = "test-proj-id"

    # Создание проекта
    response = client.post("/api/projects", json={"name": "Test Project", "description": "Test"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-proj-id"

    # Мокаем get_projects
    mock_get_projects.return_value = [{"id": "test-proj-id", "name": "Test Project", "description": "Test"}]

    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert any(p["id"] == "test-proj-id" for p in projects)

    # Мокаем get_artifacts для пустого списка
    mock_get_artifacts.return_value = []

    response = client.get("/api/projects/test-proj-id/artifacts")
    assert response.status_code == 200
    assert response.json() == []

    # Проверяем, что моки были вызваны
    mock_create_project.assert_called_once_with("Test Project", "Test")
    mock_get_projects.assert_called_once()
    mock_get_artifacts.assert_called_once_with("test-proj-id", None)
