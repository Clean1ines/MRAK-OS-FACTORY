import pytest
from unittest.mock import AsyncMock, patch, ANY
from session_service import SessionService

@pytest.fixture
def session_service():
    return SessionService()

@pytest.mark.asyncio
async def test_create_clarification_session(session_service):
    with patch("session_service.db_create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = "session-id"
        result = await session_service.create_clarification_session("proj-id", "BusinessIdea")
        assert result == "session-id"
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_get_clarification_session(session_service):
    with patch("session_service.db_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": "session-id"}
        result = await session_service.get_clarification_session("session-id")
        assert result["id"] == "session-id"
        mock_get.assert_called_once_with("session-id")

@pytest.mark.asyncio
async def test_add_message_to_session(session_service):
    with patch("session_service.db_add_message", new_callable=AsyncMock) as mock_add:
        await session_service.add_message_to_session("session-id", "user", "Hello")
        mock_add.assert_called_once_with("session-id", "user", "Hello", tx=ANY)

@pytest.mark.asyncio
async def test_list_active_sessions_for_project(session_service):
    with patch("session_service.db_list_active", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"id": "s1"}]
        result = await session_service.list_active_sessions_for_project("proj-id")
        assert len(result) == 1
        mock_list.assert_called_once_with("proj-id")
