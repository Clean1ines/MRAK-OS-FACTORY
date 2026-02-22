import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_start_clarification_session(sync_client: TestClient):
    # Создаём проект через API
    proj_resp = sync_client.post("/api/projects", json={"name": "Test Project"})
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["id"]

    # Мокаем методы prompt_service
    with patch("routers.clarification.prompt_service.get_chat_completion", new_callable=AsyncMock) as mock_get_chat, \
         patch("routers.clarification.prompt_service.synthesize_conversation_state", new_callable=AsyncMock) as mock_synthesize:

        mock_get_chat.return_value = "Первый вопрос ассистента?"
        mock_synthesize.return_value = {
            "clear_context": [],
            "unclear_context": [],
            "user_questions": [],
            "answered_questions": [],
            "next_question": None,
            "completion_score": 0.0
        }

        resp = sync_client.post("/api/clarification/start", json={
            "project_id": project_id,
            "target_artifact_type": "BusinessIdea"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["project_id"] == project_id
    assert data["target_artifact_type"] == "BusinessIdea"
    assert data["status"] == "active"
    assert len(data["history"]) == 1
    assert data["history"][0]["role"] == "assistant"
    assert data["history"][0]["content"] == "Первый вопрос ассистента?"

    session_id = data["id"]
    get_resp = sync_client.get(f"/api/clarification/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

def test_add_message_to_session(sync_client: TestClient):
    proj_resp = sync_client.post("/api/projects", json={"name": "Test Project"})
    project_id = proj_resp.json()["id"]

    with patch("routers.clarification.prompt_service.get_chat_completion", new_callable=AsyncMock) as mock_get_chat, \
         patch("routers.clarification.prompt_service.synthesize_conversation_state", new_callable=AsyncMock) as mock_synthesize:

        mock_get_chat.side_effect = [
            "Первый вопрос ассистента?",
            "Ответ ассистента на сообщение"
        ]
        mock_synthesize.return_value = {
            "clear_context": [],
            "unclear_context": [],
            "user_questions": [],
            "answered_questions": [],
            "next_question": None,
            "completion_score": 0.0
        }

        start_resp = sync_client.post("/api/clarification/start", json={
            "project_id": project_id,
            "target_artifact_type": "BusinessIdea"
        })
        session_id = start_resp.json()["id"]

        msg_resp = sync_client.post(f"/api/clarification/{session_id}/message", json={
            "message": "Я хочу создать Telegram-бота для перевода книг."
        })

    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert len(data["history"]) == 3
    assert data["history"][1]["role"] == "user"
    assert data["history"][2]["role"] == "assistant"
    assert data["history"][2]["content"] == "Ответ ассистента на сообщение"
    assert data["context_summary"] is not None

def test_complete_clarification_session(sync_client: TestClient):
    proj_resp = sync_client.post("/api/projects", json={"name": "Test Project"})
    project_id = proj_resp.json()["id"]

    with patch("routers.clarification.prompt_service.get_chat_completion", new_callable=AsyncMock) as mock_get_chat, \
         patch("routers.clarification.prompt_service.synthesize_conversation_state", new_callable=AsyncMock) as mock_synthesize:

        mock_get_chat.return_value = "Первый вопрос"
        mock_synthesize.return_value = {
            "clear_context": [],
            "unclear_context": [],
            "user_questions": [],
            "answered_questions": [],
            "next_question": None,
            "completion_score": 0.0
        }

        start_resp = sync_client.post("/api/clarification/start", json={
            "project_id": project_id,
            "target_artifact_type": "BusinessIdea"
        })
        session_id = start_resp.json()["id"]

        complete_resp = sync_client.post(f"/api/clarification/{session_id}/complete")

    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    get_resp = sync_client.get(f"/api/clarification/{session_id}")
    assert get_resp.json()["status"] == "completed"

def test_list_active_sessions(sync_client: TestClient):
    proj_resp = sync_client.post("/api/projects", json={"name": "Test Project"})
    project_id = proj_resp.json()["id"]

    with patch("routers.clarification.prompt_service.get_chat_completion", new_callable=AsyncMock) as mock_get_chat, \
         patch("routers.clarification.prompt_service.synthesize_conversation_state", new_callable=AsyncMock) as mock_synthesize:

        mock_get_chat.return_value = "Первый вопрос"
        mock_synthesize.return_value = {
            "clear_context": [],
            "unclear_context": [],
            "user_questions": [],
            "answered_questions": [],
            "next_question": None,
            "completion_score": 0.0
        }

        sync_client.post("/api/clarification/start", json={
            "project_id": project_id,
            "target_artifact_type": "BusinessIdea"
        })
        sync_client.post("/api/clarification/start", json={
            "project_id": project_id,
            "target_artifact_type": "BusinessIdea"
        })

        active_resp = sync_client.get(f"/api/projects/{project_id}/clarification/active")

    assert active_resp.status_code == 200
    sessions = active_resp.json()
    assert len(sessions) == 2
    for s in sessions:
        assert "id" in s
        assert s["target_artifact_type"] == "BusinessIdea"
        assert "created_at" in s
