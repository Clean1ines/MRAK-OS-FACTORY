import pytest
from unittest.mock import MagicMock, patch
from logic import MrakOrchestrator


@pytest.fixture
def orch():
    # Мокаем Groq при инициализации по стандартам Black
    with patch("logic.Groq") as mock_groq:
        instance = MrakOrchestrator(api_key="gsk_test_123")
        instance.client = mock_groq.return_value
        yield instance


def test_pii_filter(orch):
    test_str = "Contact admin@mrak.io with key gsk_12345678901234567890"
    filtered = orch._pii_filter(test_str)
    assert "[EMAIL_REDACTED]" in filtered
    assert "[KEY_REDACTED]" in filtered


@pytest.mark.asyncio
async def test_stream_analysis_flow(orch):
    # Создаем мок для объекта ответа
    mock_response = MagicMock()

    # Мокаем метод .get() у хедеров, чтобы он возвращал нужные строки
    def side_effect(key, default=None):
        if key == "x-ratelimit-remaining-tokens":
            return "500"
        if key == "x-ratelimit-remaining-requests":
            return "10"
        return default

    mock_response.headers.get.side_effect = side_effect

    # Мокаем чанки данных
    mock_chunk = MagicMock()
    mock_choice = MagicMock()
    mock_choice.delta.content = "AI_RESPONSE"
    mock_chunk.choices = [mock_choice]

    mock_response.parse.return_value = [mock_chunk]

    orch.client.chat.completions.with_raw_response.create.return_value = mock_response

    # Вызываем асинхронный метод, передавая обязательный аргумент mode
    gen = orch.stream_analysis("Hello", "System", "llama-model", mode="test_mode")
    results = [chunk async for chunk in gen]

    # Проверка метаданных
    assert "__METADATA__500|10__" in results[0]
    # Проверка контента
    assert "AI_RESPONSE" in results[1]
