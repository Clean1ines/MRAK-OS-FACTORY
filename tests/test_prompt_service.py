import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from prompt_service import PromptService

@pytest.fixture
def mock_groq_client():
    client = MagicMock()
    # create_completion должен быть синхронным методом, возвращающим объект с choices
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Assistant response"))]
    client.create_completion.return_value = mock_completion
    return client

@pytest.fixture
def mock_prompt_loader():
    loader = AsyncMock()
    loader.get_system_prompt.return_value = "System prompt"
    return loader

@pytest.fixture
def prompt_service(mock_groq_client, mock_prompt_loader):
    return PromptService(mock_groq_client, mock_prompt_loader, {})

@pytest.mark.asyncio
async def test_get_system_prompt(prompt_service, mock_prompt_loader):
    result = await prompt_service.get_system_prompt("02_IDEA_CLARIFIER")
    mock_prompt_loader.get_system_prompt.assert_called_once_with("02_IDEA_CLARIFIER", {})
    assert result == "System prompt"

@pytest.mark.asyncio
async def test_get_chat_completion_success(prompt_service, mock_groq_client):
    messages = [{"role": "user", "content": "Hello"}]
    result = await prompt_service.get_chat_completion(messages, "llama-3.3-70b-versatile")
    mock_groq_client.create_completion.assert_called_once_with(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.6,
        stream=False
    )
    assert result == "Assistant response"

@pytest.mark.asyncio
async def test_get_chat_completion_failure(prompt_service, mock_groq_client):
    mock_groq_client.create_completion.side_effect = Exception("API error")
    with pytest.raises(Exception, match="API error"):
        await prompt_service.get_chat_completion([], "model")

@pytest.mark.asyncio
async def test_synthesize_conversation_state(prompt_service, mock_groq_client, mock_prompt_loader):
    mock_prompt_loader.get_system_prompt.return_value = "State synthesizer prompt"
    # Настраиваем create_completion на возврат JSON
    mock_groq_client.create_completion.return_value.choices[0].message.content = (
        '{"clear_context": [], "unclear_context": [], "user_questions": [], "answered_questions": [], "next_question": null, "completion_score": 0.0}'
    )
    history = [{"role": "user", "content": "Hi"}]
    result = await prompt_service.synthesize_conversation_state(history, "model")
    assert "clear_context" in result
    assert result["completion_score"] == 0.0
