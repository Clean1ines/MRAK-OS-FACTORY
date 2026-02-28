import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from use_cases.add_message import AddMessageUseCase
from schemas import MessageRequest, ClarificationSessionResponse
import json

@pytest.fixture
def mock_orch():
    orch = AsyncMock()
    orch.type_to_mode = MagicMock()
    orch.type_to_mode.get.return_value = "02_IDEA_CLARIFIER"
    orch.get_system_prompt.return_value = "System prompt"
    orch.get_chat_completion.return_value = "Ответ ассистента"
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
    service.add_message_to_session = AsyncMock()
    service.update_clarification_session = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_add_message_success(mock_orch, mock_session_service):
    # Четыре вызова get_clarification_session:
    # 1. проверка существования
    # 2. после добавления user-сообщения
    # 3. после добавления assistant-сообщения
    # 4. финальный после синтеза
    mock_session_service.get_clarification_session.side_effect = [
        {  # вызов 1
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
        {  # вызов 2
            "id": "session-id",
            "project_id": "proj-id",
            "target_artifact_type": "BusinessIdea",
            "history": [
                {"role": "assistant", "content": "Первый вопрос"},
                {"role": "user", "content": "Я хочу бота"}
            ],
            "status": "active",
            "context_summary": None,
            "final_artifact_id": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        },
        {  # вызов 3
            "id": "session-id",
            "project_id": "proj-id",
            "target_artifact_type": "BusinessIdea",
            "history": [
                {"role": "assistant", "content": "Первый вопрос"},
                {"role": "user", "content": "Я хочу бота"},
                {"role": "assistant", "content": "Ответ ассистента"}
            ],
            "status": "active",
            "context_summary": None,
            "final_artifact_id": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        },
        {  # вызов 4 – финальный, возвращаем то же самое
            "id": "session-id",
            "project_id": "proj-id",
            "target_artifact_type": "BusinessIdea",
            "history": [
                {"role": "assistant", "content": "Первый вопрос"},
                {"role": "user", "content": "Я хочу бота"},
                {"role": "assistant", "content": "Ответ ассистента"}
            ],
            "status": "active",
            "context_summary": None,
            "final_artifact_id": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }
    ]

    req = MessageRequest(message="Я хочу бота")
    use_case = AddMessageUseCase(mock_orch, mock_session_service)
    result = await use_case.execute("session-id", req)

    assert isinstance(result, ClarificationSessionResponse)
    assert result.id == "session-id"
    assert len(result.history) == 3
    assert result.history[2]["role"] == "assistant"
    assert result.history[2]["content"] == "Ответ ассистента"

    mock_session_service.add_message_to_session.assert_any_call("session-id", "user", "Я хочу бота")
    mock_session_service.add_message_to_session.assert_any_call("session-id", "assistant", "Ответ ассистента")
    mock_orch.get_chat_completion.assert_called_once()
    mock_orch.synthesize_conversation_state.assert_called()
    mock_session_service.update_clarification_session.assert_called()

@pytest.mark.asyncio
async def test_add_message_session_not_found(mock_orch, mock_session_service):
    mock_session_service.get_clarification_session.return_value = None

    req = MessageRequest(message="test")
    use_case = AddMessageUseCase(mock_orch, mock_session_service)
    with pytest.raises(ValueError, match="Session not found"):
        await use_case.execute("session-id", req)

@pytest.mark.asyncio
async def test_add_message_session_not_active(mock_orch, mock_session_service):
    mock_session_service.get_clarification_session.return_value = {
        "id": "session-id",
        "status": "completed"
    }

    req = MessageRequest(message="test")
    use_case = AddMessageUseCase(mock_orch, mock_session_service)
    with pytest.raises(ValueError, match="Session is not active"):
        await use_case.execute("session-id", req)

@pytest.mark.asyncio
async def test_add_message_no_mode(mock_orch, mock_session_service):
    mock_orch.type_to_mode.get.return_value = None
    # Возвращаем полную сессию с историей
    mock_session_service.get_clarification_session.return_value = {
        "id": "session-id",
        "project_id": "proj-id",
        "target_artifact_type": "Unknown",
        "history": [{"role": "assistant", "content": "Первый вопрос"}],  # ADDED
        "status": "active",
        "context_summary": None,
        "final_artifact_id": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00"
    }

    req = MessageRequest(message="test")
    use_case = AddMessageUseCase(mock_orch, mock_session_service)
    with pytest.raises(ValueError, match="No prompt mode found"):
        await use_case.execute("session-id", req)

@pytest.mark.asyncio
async def test_add_message_llm_fails(mock_orch, mock_session_service):
    mock_orch.get_chat_completion.side_effect = Exception("LLM error")
    # Возвращаем полную сессию
    mock_session_service.get_clarification_session.return_value = {
        "id": "session-id",
        "project_id": "proj-id",
        "target_artifact_type": "BusinessIdea",
        "history": [],
        "status": "active",
        "context_summary": None,
        "final_artifact_id": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00"
    }

    req = MessageRequest(message="test")
    use_case = AddMessageUseCase(mock_orch, mock_session_service)
    with pytest.raises(RuntimeError, match="Failed to generate assistant message"):
        await use_case.execute("session-id", req)
