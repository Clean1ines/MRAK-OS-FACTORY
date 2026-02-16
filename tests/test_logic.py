import pytest
from unittest.mock import MagicMock, patch
from logic import MrakOrchestrator


@pytest.fixture
def orch():
    # Мокаем Groq при инициализации
    with patch("logic.Groq") as mock_groq:
        instance = MrakOrchestrator(api_key="gsk_test_123")
        instance.client = mock_groq.return_value
        yield instance


def test_pii_filter(orch):
    test_str = "Contact admin@mrak.io with key gsk_12345678901234567890"
    filtered = orch._pii_filter(test_str)
    assert "[EMAIL_REDACTED]" in filtered
    assert "[KEY_REDACTED]" in filtered


def test_stream_analysis_flow(orch):
    # Создаем сложный мок для context manager (with client...raw_response)
    mock_response = MagicMock()
    mock_response.headers = {
        "x-ratelimit-remaining-tokens": "500",
        "x-ratelimit-remaining-requests": "10",
    }

    # Мокаем чанки данных
    mock_chunk = MagicMock()
    mock_chunk.choices[0].delta.content = "AI_RESPONSE"
    mock_response.parse.return_value = [mock_chunk]

    # Настраиваем вход в контекстный менеджер
    orch.client.chat.completions.with_raw_response.create.return_value.__enter__.return_value = (
        mock_response
    )

    gen = orch.stream_analysis("Hello", "System", "llama-model")
    results = list(gen)

    # Проверка метаданных
    assert "__METADATA__500|10__" in results[0]
    # Проверка контента
    assert "AI_RESPONSE" in results[1]
