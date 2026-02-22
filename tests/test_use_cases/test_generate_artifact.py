import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from use_cases.generate_artifact import GenerateArtifactUseCase
from schemas import GenerateArtifactRequest
from validation import ValidationError

@pytest.fixture
def mock_orch():
    orch = AsyncMock()
    orch.generate_business_requirements.return_value = [{"id": "req1"}]
    orch.generate_req_engineering_analysis.return_value = {"analysis": "data"}
    orch.generate_functional_requirements.return_value = [{"id": "func1"}]
    orch.generate_artifact.return_value = "new-id"
    return orch

@pytest.mark.asyncio
async def test_generate_business_requirements(mock_orch):
    req = GenerateArtifactRequest(
        artifact_type="BusinessRequirementPackage",
        parent_id="parent-id",
        feedback="feedback",
        model="model",
        project_id="proj-id",
        existing_content=None
    )
    use_case = GenerateArtifactUseCase(mock_orch)
    result = await use_case.execute(req)

    assert result == {"result": [{"id": "req1"}]}
    mock_orch.generate_business_requirements.assert_called_once_with(
        analysis_id="parent-id",
        user_feedback="feedback",
        model_id="model",
        project_id="proj-id",
        existing_requirements=None
    )

@pytest.mark.asyncio
async def test_generate_req_engineering_analysis(mock_orch):
    req = GenerateArtifactRequest(
        artifact_type="ReqEngineeringAnalysis",
        parent_id="parent-id",
        feedback="feedback",
        model="model",
        project_id="proj-id",
        existing_content=None
    )
    use_case = GenerateArtifactUseCase(mock_orch)
    result = await use_case.execute(req)

    assert result == {"result": {"analysis": "data"}}
    mock_orch.generate_req_engineering_analysis.assert_called_once_with(
        parent_id="parent-id",
        user_feedback="feedback",
        model_id="model",
        project_id="proj-id",
        existing_analysis=None
    )

@pytest.mark.asyncio
async def test_generate_functional_requirements(mock_orch):
    req = GenerateArtifactRequest(
        artifact_type="FunctionalRequirementPackage",
        parent_id="parent-id",
        feedback="feedback",
        model="model",
        project_id="proj-id",
        existing_content=None
    )
    use_case = GenerateArtifactUseCase(mock_orch)
    result = await use_case.execute(req)

    assert result == {"result": [{"id": "func1"}]}
    mock_orch.generate_functional_requirements.assert_called_once_with(
        analysis_id="parent-id",
        user_feedback="feedback",
        model_id="model",
        project_id="proj-id",
        existing_requirements=None
    )

@pytest.mark.asyncio
async def test_generate_other_artifact(mock_orch):
    with patch("use_cases.generate_artifact.db.get_artifact", new_callable=AsyncMock) as mock_get_artifact, \
         patch("use_cases.generate_artifact.transaction") as mock_transaction:

        # Настраиваем side_effect для двух вызовов get_artifact
        mock_get_artifact.side_effect = [
            {"id": "parent-id", "content": {}},  # для родителя
            {"id": "new-id", "content": {"code": "print('hello')"}}  # для результата
        ]
        mock_transaction.return_value.__aenter__.return_value = None

        req = GenerateArtifactRequest(
            artifact_type="CodeArtifact",
            parent_id="parent-id",
            feedback="feedback",
            model="model",
            project_id="proj-id",
            existing_content=None
        )
        use_case = GenerateArtifactUseCase(mock_orch)
        result = await use_case.execute(req)

        assert result == {"result": {"code": "print('hello')"}}
        mock_orch.generate_artifact.assert_called_once_with(
            artifact_type="CodeArtifact",
            user_input="feedback",
            parent_artifact={"id": "parent-id", "content": {}},
            model_id="model",
            project_id="proj-id"
        )

@pytest.mark.asyncio
async def test_generate_validation_error(mock_orch):
    mock_orch.generate_business_requirements.side_effect = ValidationError("Invalid")

    req = GenerateArtifactRequest(
        artifact_type="BusinessRequirementPackage",
        parent_id="parent-id",
        feedback="",
        model=None,
        project_id="proj-id",
        existing_content=None
    )
    use_case = GenerateArtifactUseCase(mock_orch)
    with pytest.raises(ValidationError):
        await use_case.execute(req)
