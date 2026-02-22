# CHANGED: Test use case instead of orchestrator
import pytest
from unittest.mock import AsyncMock, patch
from use_cases.generate_artifact import GenerateArtifactUseCase
from schemas import GenerateArtifactRequest
from artifact_service import ArtifactService

@pytest.mark.asyncio
async def test_generate_business_requirements_success():
    mock_artifact_service = AsyncMock(spec=ArtifactService)
    fake_requirements = [{"description": "Test requirement", "priority": "HIGH"}]
    mock_artifact_service.generate_business_requirements.return_value = fake_requirements

    use_case = GenerateArtifactUseCase(mock_artifact_service)
    req = GenerateArtifactRequest(
        artifact_type="BusinessRequirementPackage",
        parent_id="analysis-id",
        feedback="feedback",
        model="model",  # CHANGED: was model_id, now model
        project_id="proj-id",
        existing_content=None
    )
    result = await use_case.execute(req)

    assert result == {"result": fake_requirements}
    mock_artifact_service.generate_business_requirements.assert_called_once_with(
        analysis_id="analysis-id",
        user_feedback="feedback",
        model_id="model",  # здесь ожидается model_id
        project_id="proj-id",
        existing_requirements=None
    )
