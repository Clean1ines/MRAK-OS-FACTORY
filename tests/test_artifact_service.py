# CHANGED: Fixed patch paths to target the actual module where functions are used
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
    mode_map = {"04_BUSINESS_REQ_GEN": "url", "05_REQ_ENG_COUNCIL": "url", "17_FUNCTIONAL_REQ_GEN": "url"}
    type_to_mode = {
        "BusinessRequirementPackage": "04_BUSINESS_REQ_GEN",
        "ReqEngineeringAnalysis": "05_REQ_ENG_COUNCIL",
        "FunctionalRequirementPackage": "17_FUNCTIONAL_REQ_GEN"
    }
    return ArtifactService(mock_groq_client, mock_prompt_loader, mode_map, type_to_mode)

@pytest.mark.asyncio
async def test_generate_artifact_success(artifact_service, mock_groq_client):
    # CHANGED: patch save_artifact where it's used: artifact_service.save_artifact
    with patch("artifact_service.save_artifact", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = "artifact-id"

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
async def test_generate_artifact_validation_failure(artifact_service, mock_groq_client):
    mock_groq_client.create_completion.return_value.choices[0].message.content = '{"key": "value"}'
    # No need to mock save_artifact; validation should fail before saving
    with pytest.raises(ValidationError):
        await artifact_service.generate_artifact(
            artifact_type="BusinessRequirementPackage",
            user_input="Test",
            parent_artifact=None
        )

@pytest.mark.asyncio
async def test_generate_business_requirements_success(artifact_service, mock_groq_client):
    # CHANGED: patch get_artifact inside the generator module
    mock_get_artifact = AsyncMock(return_value={
        "id": "analysis-id",  # This ID is not used in a real query because we mock the function
        "type": "ProductCouncilAnalysis",
        "content": {"some": "data"},
        "parent_id": None
    })
    with patch("generators.business_requirements.get_artifact", mock_get_artifact), \
         patch("artifact_service.save_artifact", new_callable=AsyncMock) as mock_save:  # not used, but kept

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
        mock_save.assert_not_called()
