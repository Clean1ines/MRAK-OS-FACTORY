import pytest
from unittest.mock import MagicMock, patch
from logic import MrakOrchestrator

@pytest.fixture
def orch():
    with patch('logic.Groq') as mock_groq:
        instance = MrakOrchestrator(api_key="gsk_test_key_1234567890")
        instance.client = mock_groq.return_value
        yield instance

def test_pii_filter(orch):
    input_text = "Contact dev@mrak.io with key gsk_12345678901234567890"
    filtered = orch._pii_filter(input_text)
    assert "[EMAIL_REDACTED]" in filtered
    assert "[KEY_REDACTED]" in filtered

def test_process_stream_success(orch):
    # Имитируем чанки стрима
    mock_chunk = MagicMock()
    mock_chunk.choices[0].delta.content = "Успех"
    orch.client.chat.completions.create.return_value = [mock_chunk]
    
    gen = orch.process_request_stream("Тест")
    results = list(gen)
    
    assert results[0]["success"] is True
    assert "Успех" in results[0]["full_content"]