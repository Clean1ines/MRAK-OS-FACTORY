import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from use_cases.start_clarification import StartClarificationUseCase
from schemas import StartClarificationRequest, ClarificationSessionResponse
import json

@pytest.fixture
def mock_orch():
    orch = AsyncMock()
    orch.type_to_mode = MagicMock()
    orch.type_to_mode.get.return_value = "02_IDEA_CLARIFIER"
    orch.get_system_prompt.return_value = "System prompt"
    orch.get_chat_completion.return_value = "Первый вопрос"
    orch.synthesize_conversation_state.return_value = {
        "clear_context": [],
        "unclear_context": [],
        "user_questions": [],
        "answered_questions": [],
        "next_question": None,
        "completion_score": 0.0
    }
    return orch

@pytest.fixture
def mock_session_service():
    service = AsyncMock()
    service.create_clarification_session.return_value = "session-id"
    # Убираем None, оставляем только сессии – 3 элемента для надёжности
    service.get_clarification_session.side_effect = [
        {
            "id": "session-id",
            "project_id": "proj-id",
            "target_artifact_type": "BusinessIdea",
            "history": [{"role": "assistant", "content": "Первый вопрос"}],
            "status": "active",
            "context_summary": None,
            "final_artifact_id": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        },
        {
            "id": "session-id",
            "project_id": "proj-id",
            "target_artifact_type": "BusinessIdea",
            "history": [{"role": "assistant", "content": "Первый вопрос"}],
            "status": "active",
            "context_summary": None,
            "final_artifact_id": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        },
        {
            "id": "session-id",
            "project_id": "proj-id",
            "target_artifact_type": "BusinessIdea",
            "history": [{"role": "assistant", "content": "Первый вопрос"}],
            "status": "active",
            "context_summary": None,
            "final_artifact_id": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }
    ]
    service.add_message_to_session = AsyncMock()
    service.update_clarification_session = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_start_clarification_success(mock_orch, mock_session_service):
    with patch("use_cases.start_clarification.db.get_project", new_callable=AsyncMock) as mock_get_project:
        mock_get_project.return_value = {"id": "proj-id"}

        req = StartClarificationRequest(
            project_id="proj-id",
            target_artifact_type="BusinessIdea",
            model="llama-3.3-70b-versatile"
        )

        use_case = StartClarificationUseCase(mock_orch, mock_session_service)
        result = await use_case.execute(req)

        assert isinstance(result, ClarificationSessionResponse)
        assert result.id == "session-id"
        assert result.project_id == "proj-id"
        assert result.target_artifact_type == "BusinessIdea"
        assert len(result.history) == 1
        assert result.history[0]["role"] == "assistant"
        assert result.history[0]["content"] == "Первый вопрос"

        mock_get_project.assert_called_once_with("proj-id", tx=ANY)
        mock_orch.get_chat_completion.assert_called_once()
        mock_session_service.create_clarification_session.assert_called_once_with("proj-id", "BusinessIdea")
        mock_session_service.add_message_to_session.assert_called_once_with("session-id", "assistant", "Первый вопрос")
        # Теперь update_clarification_session должен быть вызван
        mock_session_service.update_clarification_session.assert_called_once()

@pytest.mark.asyncio
async def test_start_clarification_project_not_found(mock_orch, mock_session_service):
    with patch("use_cases.start_clarification.db.get_project", new_callable=AsyncMock) as mock_get_project:
        mock_get_project.return_value = None

        req = StartClarificationRequest(
            project_id="proj-id",
            target_artifact_type="BusinessIdea"
        )

        use_case = StartClarificationUseCase(mock_orch, mock_session_service)
        with pytest.raises(ValueError, match="Project not found"):
            await use_case.execute(req)

@pytest.mark.asyncio
async def test_start_clarification_no_mode(mock_orch, mock_session_service):
    mock_orch.type_to_mode.get.return_value = None

    with patch("use_cases.start_clarification.db.get_project", new_callable=AsyncMock) as mock_get_project:
        mock_get_project.return_value = {"id": "proj-id"}

        req = StartClarificationRequest(
            project_id="proj-id",
            target_artifact_type="UnknownType"
        )

        use_case = StartClarificationUseCase(mock_orch, mock_session_service)
        with pytest.raises(ValueError, match="No prompt mode found"):
            await use_case.execute(req)

@pytest.mark.asyncio
async def test_start_clarification_llm_fails(mock_orch, mock_session_service):
    mock_orch.get_chat_completion.side_effect = Exception("LLM error")

    with patch("use_cases.start_clarification.db.get_project", new_callable=AsyncMock) as mock_get_project:
        mock_get_project.return_value = {"id": "proj-id"}

        req = StartClarificationRequest(
            project_id="proj-id",
            target_artifact_type="BusinessIdea"
        )

        use_case = StartClarificationUseCase(mock_orch, mock_session_service)
        with pytest.raises(RuntimeError, match="Failed to generate first message"):
            await use_case.execute(req)
