# tests/test_artifact_service.py
import pytest
import json
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock, call, ANY

from artifact_service import ArtifactService
from validation import ValidationError

def mock_llm_response(content: str):
    """Создаёт фиктивный ответ LLM."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def mock_groq_client(mocker):
    mock = MagicMock()
    mock.create_completion = MagicMock()
    return mock

@pytest.fixture
def mock_save_artifact(mocker):
    mock = AsyncMock(return_value=str(uuid.uuid4()))
    mocker.patch('artifact_service.save_artifact', mock)
    return mock

@pytest.fixture
def mock_transaction(mocker):
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mocker.patch('artifact_service.transaction', return_value=mock_ctx)
    return mock_ctx

@pytest.fixture
def artifact_service(mock_groq_client):
    return ArtifactService(groq_client=mock_groq_client)

@pytest.fixture
def sample_artifact():
    return {"id": "art-123", "type": "test_type", "content": {"some": "data"}}

@pytest.fixture
def sample_generation_config():
    return {
        "system_prompt": "You are a test assistant.",
        "user_prompt_template": "Input artifacts:\n{all_artifacts}\nFeedback: {user_input}",
        "required_input_types": ["test_type"]
    }

# ----------------------------------------------------------------------
# Тесты для generate_artifact
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_artifact_success_basic(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    sample_artifact,
    mocker
):
    """Базовый успешный сценарий."""
    config = {"system_prompt": "Test prompt"}
    input_artifacts = [sample_artifact]
    user_input = "some feedback"
    model_id = "test-model"
    project_id = "proj-123"
    expected_artifact_id = "new-art-456"

    mock_groq_client.create_completion.return_value = mock_llm_response('{"result": "ok"}')
    mock_save_artifact.return_value = expected_artifact_id

    result = await artifact_service.generate_artifact(
        artifact_type="test_type",
        input_artifacts=input_artifacts,
        user_input=user_input,
        model_id=model_id,
        project_id=project_id,
        generation_config=config
    )

    assert result == expected_artifact_id
    mock_groq_client.create_completion.assert_called_once()
    call_args = mock_groq_client.create_completion.call_args[1]
    assert call_args["model"] == model_id
    messages = call_args["messages"]
    assert messages[0]["content"] == "Test prompt"
    assert "--- test_type (id: art-123) ---" in messages[1]["content"]
    assert user_input in messages[1]["content"]

    mock_save_artifact.assert_awaited_once_with(
        artifact_type="test_type",
        content={"result": "ok"},
        owner="system",
        status="GENERATED",
        project_id=project_id,
        parent_id=None,
        tx=ANY
    )

@pytest.mark.asyncio
async def test_generate_artifact_success_with_template(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    sample_artifact,
    sample_generation_config,
    mocker
):
    """Успех с пользовательским шаблоном."""
    input_artifacts = [sample_artifact]
    user_input = "hello"
    expected_artifact_id = "new-id"

    mock_groq_client.create_completion.return_value = mock_llm_response('{"data": 123}')
    mock_save_artifact.return_value = expected_artifact_id

    result = await artifact_service.generate_artifact(
        artifact_type="test_type",
        input_artifacts=input_artifacts,
        user_input=user_input,
        model_id="model",
        project_id="proj",
        generation_config=sample_generation_config
    )

    assert result == expected_artifact_id
    call_args = mock_groq_client.create_completion.call_args[1]
    user_prompt = call_args["messages"][1]["content"]
    assert "Input artifacts:" in user_prompt
    assert '"some": "data"' in user_prompt
    assert user_input in user_prompt

@pytest.mark.asyncio
async def test_generate_artifact_no_input_artifacts(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """input_artifacts=None должен превратиться в пустой список."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response('{"ok": true}')
    mock_save_artifact.return_value = "id"

    result = await artifact_service.generate_artifact(
        artifact_type="t",
        input_artifacts=None,
        user_input="",
        model_id="m",
        project_id="p",
        generation_config=config
    )

    assert result == "id"
    user_prompt = mock_groq_client.create_completion.call_args[1]["messages"][1]["content"]
    assert "Context:\n\n\nUser input:" in user_prompt

@pytest.mark.asyncio
async def test_generate_artifact_empty_input_artifacts(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Пустой список входных артефактов."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response('{"ok": true}')
    mock_save_artifact.return_value = "id"

    result = await artifact_service.generate_artifact(
        artifact_type="t",
        input_artifacts=[],
        user_input="",
        model_id="m",
        project_id="p",
        generation_config=config
    )

    assert result == "id"
    user_prompt = mock_groq_client.create_completion.call_args[1]["messages"][1]["content"]
    assert "Context:\n\n\nUser input:" in user_prompt

@pytest.mark.asyncio
async def test_generate_artifact_required_types_match(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    sample_artifact,
    mocker
):
    """required_input_types совпадают – переменная подставляется."""
    config = {
        "system_prompt": "Test",
        "user_prompt_template": "Type value: {test_type}",
        "required_input_types": ["test_type"]
    }
    input_artifacts = [sample_artifact]
    mock_groq_client.create_completion.return_value = mock_llm_response('{}')
    mock_save_artifact.return_value = "id"

    await artifact_service.generate_artifact(
        artifact_type="t",
        input_artifacts=input_artifacts,
        user_input="",
        model_id="m",
        project_id="p",
        generation_config=config
    )

    user_prompt = mock_groq_client.create_completion.call_args[1]["messages"][1]["content"]
    assert '"some": "data"' in user_prompt

@pytest.mark.asyncio
async def test_generate_artifact_required_types_missing(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    sample_artifact,
    mocker,
    caplog
):
    """required_input_types отсутствуют – логируется предупреждение и подставляется пустая строка."""
    config = {
        "system_prompt": "Test",
        "user_prompt_template": "Missing: {missing_type}",
        "required_input_types": ["missing_type"]
    }
    input_artifacts = [sample_artifact]
    mock_groq_client.create_completion.return_value = mock_llm_response('{}')
    mock_save_artifact.return_value = "id"

    with caplog.at_level(logging.WARNING):
        await artifact_service.generate_artifact(
            artifact_type="t",
            input_artifacts=input_artifacts,
            user_input="",
            model_id="m",
            project_id="p",
            generation_config=config
        )

    assert "Required input type 'missing_type' not found" in caplog.text
    user_prompt = mock_groq_client.create_completion.call_args[1]["messages"][1]["content"]
    assert "Missing: " in user_prompt

@pytest.mark.asyncio
async def test_generate_artifact_non_json_response_allowed(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Ответ не JSON, но тип не требует JSON – оборачивается в {"text": ...}."""
    # Патчим REQUIRED_FIELDS пустым словарём, чтобы тест не зависел от реальных значений
    mocker.patch('artifact_service.REQUIRED_FIELDS', {})
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response("Just plain text")

    await artifact_service.generate_artifact(
        artifact_type="any_type",
        input_artifacts=[],
        user_input="",
        model_id="m",
        project_id="p",
        generation_config=config
    )

    mock_save_artifact.assert_awaited_once()
    saved_content = mock_save_artifact.call_args[1]["content"]
    assert saved_content == {"text": "Just plain text"}

@pytest.mark.asyncio
async def test_generate_artifact_retry_then_success(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Первая попытка – исключение, вторая – успех."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.side_effect = [
        Exception("API error"),
        mock_llm_response('{"valid": true}')
    ]
    mocker.patch('asyncio.sleep', return_value=None)
    mock_save_artifact.return_value = "id"

    result = await artifact_service.generate_artifact(
        artifact_type="t",
        input_artifacts=[],
        user_input="",
        model_id="m",
        project_id="p",
        generation_config=config
    )

    assert result == "id"
    assert mock_groq_client.create_completion.call_count == 2

@pytest.mark.asyncio
async def test_generate_artifact_all_retries_fail(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Все попытки проваливаются – выбрасывается ValidationError."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.side_effect = Exception("API error")
    mocker.patch('asyncio.sleep', return_value=None)

    with pytest.raises(ValidationError, match="Failed to generate valid t after 4 attempts"):
        await artifact_service.generate_artifact(
            artifact_type="t",
            input_artifacts=[],
            user_input="",
            model_id="m",
            project_id="p",
            generation_config=config
        )
    assert mock_groq_client.create_completion.call_count == 4

@pytest.mark.asyncio
async def test_generate_artifact_missing_system_prompt(
    artifact_service,
    mock_groq_client,
    mock_save_artifact
):
    """Отсутствие system_prompt в generation_config – ValueError."""
    config = {}
    with pytest.raises(ValueError, match="generation_config must contain 'system_prompt'"):
        await artifact_service.generate_artifact(
            artifact_type="t",
            input_artifacts=[],
            user_input="",
            model_id="m",
            project_id="p",
            generation_config=config
        )
    mock_groq_client.create_completion.assert_not_called()
    mock_save_artifact.assert_not_called()

@pytest.mark.asyncio
async def test_generate_artifact_validation_failure(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Валидация JSON не проходит – повтор до успеха."""
    # Для этого теста нужен мок validate_json_output, но мы его не создали в фикстурах.
    # Создадим его локально.
    mock_validate = MagicMock()
    mocker.patch('artifact_service.validate_json_output', mock_validate)

    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response('{"bad": "data"}')
    mock_validate.side_effect = [
        ValueError("Validation failed"),
        (True, "OK")
    ]
    mocker.patch('asyncio.sleep', return_value=None)
    mock_save_artifact.return_value = "id"

    result = await artifact_service.generate_artifact(
        artifact_type="t",
        input_artifacts=[],
        user_input="",
        model_id="m",
        project_id="p",
        generation_config=config
    )

    assert result == "id"
    assert mock_groq_client.create_completion.call_count == 2
    assert mock_validate.call_count == 2

@pytest.mark.asyncio
async def test_generate_artifact_save_artifact_fails(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Ошибка при сохранении артефакта пробрасывается наружу."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response('{"ok": true}')
    mock_save_artifact.side_effect = Exception("DB error")

    with pytest.raises(Exception, match="DB error"):
        await artifact_service.generate_artifact(
            artifact_type="t",
            input_artifacts=[],
            user_input="",
            model_id="m",
            project_id="p",
            generation_config=config
        )

@pytest.mark.asyncio
async def test_generate_artifact_logging_warning(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    caplog,
    mocker
):
    """Проверка логирования предупреждения при отсутствии обязательного типа."""
    config = {
        "system_prompt": "Test",
        "user_prompt_template": "Template {missing}",
        "required_input_types": ["missing"]
    }
    mock_groq_client.create_completion.return_value = mock_llm_response('{}')
    mock_save_artifact.return_value = "id"

    with caplog.at_level(logging.WARNING):
        await artifact_service.generate_artifact(
            artifact_type="t",
            input_artifacts=[],
            user_input="",
            model_id="m",
            project_id="p",
            generation_config=config
        )

    assert "Required input type 'missing' not found" in caplog.text

@pytest.mark.asyncio
async def test_generate_artifact_default_model(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Если model_id не передан, используется дефолтная модель."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response('{}')
    mock_save_artifact.return_value = "id"

    await artifact_service.generate_artifact(
        artifact_type="t",
        input_artifacts=[],
        user_input="",
        model_id=None,
        project_id="p",
        generation_config=config
    )

    call_args = mock_groq_client.create_completion.call_args[1]
    assert call_args["model"] == "llama-3.3-70b-versatile"

@pytest.mark.asyncio
async def test_generate_artifact_with_transaction_error(
    artifact_service,
    mock_groq_client,
    mock_save_artifact,
    mock_transaction,
    mocker
):
    """Ошибка внутри транзакции пробрасывается."""
    config = {"system_prompt": "Test"}
    mock_groq_client.create_completion.return_value = mock_llm_response('{}')
    mock_transaction.__aenter__.side_effect = Exception("Transaction failed")

    with pytest.raises(Exception, match="Transaction failed"):
        await artifact_service.generate_artifact(
            artifact_type="t",
            input_artifacts=[],
            user_input="",
            model_id="m",
            project_id="p",
            generation_config=config
        )
