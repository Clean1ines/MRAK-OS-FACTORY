# CHANGED: Fixed test_synthesizer_build_prompt to expect last 4 messages
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from prompt_service import PromptService
from domain.conversation_state import ConversationStateSynthesizer

# ===== Existing PromptService tests =====

@pytest.fixture
def mock_groq_client():
    client = MagicMock()
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
    mock_groq_client.create_completion.return_value.choices[0].message.content = (
        '{"clear_context": [], "unclear_context": [], "user_questions": [], "answered_questions": [], "next_question": null, "completion_score": 0.0}'
    )
    history = [{"role": "user", "content": "Hi"}]
    result = await prompt_service.synthesize_conversation_state(history, "model")
    assert "clear_context" in result
    assert result["completion_score"] == 0.0

# ===== New tests for ConversationStateSynthesizer =====

@pytest.fixture
def mock_prompt_service():
    service = AsyncMock()
    service.get_system_prompt = AsyncMock(return_value="State synthesizer prompt")
    service.get_chat_completion = AsyncMock(return_value='{"clear_context": [], "unclear_context": [], "user_questions": [], "answered_questions": [], "next_question": null, "completion_score": 0.0}')
    return service

def test_synthesizer_build_prompt():
    service = AsyncMock()
    synth = ConversationStateSynthesizer(service)
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "Fine"},
        {"role": "user", "content": "Great"}
    ]
    # Only last 4 messages should be included
    expected = "assistant: Hi\nuser: How are you?\nassistant: Fine\nuser: Great"
    result = synth.build_prompt(history)
    assert result == expected

def test_synthesizer_parse_response_valid():
    service = AsyncMock()
    synth = ConversationStateSynthesizer(service)
    response = '{"clear_context": ["a"], "unclear_context": [], "user_questions": [], "answered_questions": [], "next_question": null, "completion_score": 0.5}'
    state = synth.parse_response(response)
    assert state["clear_context"] == ["a"]
    assert state["completion_score"] == 0.5
    assert state["next_question"] is None

def test_synthesizer_parse_response_with_markdown():
    service = AsyncMock()
    synth = ConversationStateSynthesizer(service)
    response = '```json\n{"clear_context": [], "unclear_context": [], "user_questions": [], "answered_questions": [], "next_question": null, "completion_score": 0.0}\n```'
    state = synth.parse_response(response)
    assert state["completion_score"] == 0.0

def test_synthesizer_parse_response_missing_fields():
    service = AsyncMock()
    synth = ConversationStateSynthesizer(service)
    response = '{"clear_context": []}'
    state = synth.parse_response(response)
    assert state["clear_context"] == []
    assert state["unclear_context"] == []
    assert state["user_questions"] == []
    assert state["answered_questions"] == []
    assert state["next_question"] is None
    assert state["completion_score"] == 0.0

def test_synthesizer_parse_response_invalid_json():
    service = AsyncMock()
    synth = ConversationStateSynthesizer(service)
    response = "not json"
    state = synth.parse_response(response)
    assert state["completion_score"] == 0.0
    assert state["clear_context"] == []
    assert state["next_question"] is None

@pytest.mark.asyncio
async def test_synthesizer_synthesize_success(mock_prompt_service):
    synth = ConversationStateSynthesizer(mock_prompt_service)
    history = [{"role": "user", "content": "Hi"}]
    result = await synth.synthesize(history, "model")
    mock_prompt_service.get_system_prompt.assert_called_once_with("02sum_STATE_SYNTHESIZER")
    mock_prompt_service.get_chat_completion.assert_called_once()
    assert result["completion_score"] == 0.0

@pytest.mark.asyncio
async def test_synthesizer_synthesize_prompt_error(mock_prompt_service):
    mock_prompt_service.get_system_prompt.return_value = "System Error: something"
    synth = ConversationStateSynthesizer(mock_prompt_service)
    history = [{"role": "user", "content": "Hi"}]
    result = await synth.synthesize(history, "model")
    assert result["completion_score"] == 0.0
    mock_prompt_service.get_chat_completion.assert_not_called()
