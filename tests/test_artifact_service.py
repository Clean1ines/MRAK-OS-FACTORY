import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from artifact_service import ArtifactService, ValidationError

@pytest.fixture
def mock_groq_client():
    client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps([{
        "description": "Test requirement",
        "priority": "HIGH",
        "stakeholder": "User",
        "acceptance_criteria": ["criterion 1"],
        "business_value": "Test value"
    }])))]
    client.create_completion.return_value = mock_completion
    return client

@pytest.fixture
def mock_prompt_loader():
    loader = AsyncMock()
    loader.get_system_prompt.return_value = "System prompt"
    return loader

@pytest.fixture
def artifact_service(mock_groq_client, mock_prompt_loader):
    mode_map = {"04_BUSINESS_REQ_GEN": "url"}
    type_to_mode = {"BusinessRequirementPackage": "04_BUSINESS_REQ_GEN"}
    return ArtifactService(mock_groq_client, mock_prompt_loader, mode_map, type_to_mode)

@pytest.mark.asyncio
async def test_generate_artifact_success(artifact_service, mock_groq_client, monkeypatch):
    mock_save = AsyncMock(return_value="artifact-id")
    monkeypatch.setattr("artifact_service.save_artifact", mock_save)

    result = await artifact_service.generate_artifact(
        artifact_type="BusinessRequirementPackage",
        user_input="Test input",
        parent_artifact=None,
        model_id="model",
        project_id="proj-id"
    )

    assert result == "artifact-id"
    mock_groq_client.create_completion.assert_called_once()
    mock_save.assert_called_once()

@pytest.mark.asyncio
async def test_generate_artifact_validation_failure(artifact_service, mock_groq_client, monkeypatch):
    mock_groq_client.create_completion.return_value.choices[0].message.content = '{"key": "value"}'
    mock_save = AsyncMock()
    monkeypatch.setattr("artifact_service.save_artifact", mock_save)

    with pytest.raises(ValidationError):
        await artifact_service.generate_artifact(
            artifact_type="BusinessRequirementPackage",
            user_input="Test",
            parent_artifact=None
        )

@pytest.mark.asyncio
async def test_generate_business_requirements_success(artifact_service, mock_groq_client, monkeypatch):
    mock_get_artifact = AsyncMock(return_value={
        "id": "analysis-id",
        "type": "ProductCouncilAnalysis",
        "content": {"some": "data"},
        "parent_id": None
    })
    monkeypatch.setattr("artifact_service.get_artifact", mock_get_artifact)
    mock_save = AsyncMock()
    monkeypatch.setattr("artifact_service.save_artifact", mock_save)

    mock_groq_client.create_completion.return_value.choices[0].message.content = json.dumps([{
        "description": "Req",
        "priority": "HIGH",
        "stakeholder": "User",
        "acceptance_criteria": [],
        "business_value": "Value"
    }])

    result = await artifact_service.generate_business_requirements(
        analysis_id="analysis-id",
        user_feedback="feedback"
    )

    assert isinstance(result, list)
    assert result[0]["description"] == "Req"
