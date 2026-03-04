import pytest
from unittest.mock import AsyncMock, patch
from use_cases.generate_artifact import GenerateArtifactUseCase
from schemas import GenerateArtifactRequest

@pytest.mark.asyncio
async def test_generate_artifact_use_case():
    mock_service = AsyncMock()
    mock_service.generate_artifact.return_value = "new-id"
    use_case = GenerateArtifactUseCase(mock_service)

    req = GenerateArtifactRequest(
        artifact_type="TestType",
        parent_id="parent-id",
        feedback="feedback",
        project_id="proj-id"
    )

    with patch("use_cases.generate_artifact.db.get_artifact", new_callable=AsyncMock) as mock_get, \
         patch("use_cases.generate_artifact.transaction"):

        mock_get.side_effect = [{"id": "parent-id", "content": {}}, {"id": "new-id", "content": {"result": "ok"}}]

        result = await use_case.execute(req)

        assert result == {"result": {"result": "ok"}}
        mock_service.generate_artifact.assert_called_once_with(
            artifact_type="TestType",
            input_artifacts=[{"id": "parent-id", "content": {}}],
            user_input="feedback",
            model_id=None,
            project_id="proj-id"
        )
