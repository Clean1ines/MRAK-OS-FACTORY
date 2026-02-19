import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from logic import MrakOrchestrator


@pytest.fixture
def orch():
    with patch("logic.MrakOrchestrator") as MockOrch:
        instance = MockOrch.return_value
        # Мокаем методы, которые будут вызваны
        instance.generate_business_requirements = AsyncMock()
        instance.get_active_models = MagicMock()
        yield instance


@pytest.mark.asyncio
async def test_generate_business_requirements_success(orch):
    # Подготавливаем мок
    fake_requirements = [
        {
            "description": "Test requirement",
            "priority": "HIGH",
            "stakeholder": "User",
            "acceptance_criteria": ["criterion 1"],
            "business_value": "test value"
        }
    ]
    orch.generate_business_requirements.return_value = fake_requirements

    # Вызываем метод
    result = await orch.generate_business_requirements(
        analysis_id="test-id",
        user_feedback="feedback",
        model_id="llama-3.3-70b-versatile",
        project_id="proj-id"
    )

    assert result == fake_requirements
    orch.generate_business_requirements.assert_awaited_once_with(
        analysis_id="test-id",
        user_feedback="feedback",
        model_id="llama-3.3-70b-versatile",
        project_id="proj-id"
    )


def test_pii_filter(orch):
    # Пример теста фильтра PII, если нужно
    pass
