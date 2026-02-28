import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from use_cases.execute_workflow_step import ExecuteWorkflowStepUseCase
from validation import ValidationError

@pytest.fixture
def mock_orch():
    orch = AsyncMock()
    orch.get_next_step.return_value = {
        "next_stage": "ProductCouncilAnalysis",
        "prompt_type": "03_PRODUCT_COUNCIL",
        "parent_id": "parent-id",
        "description": "test"
    }
    orch.execute_step.return_value = {
        "artifact_id": "new-id",
        "artifact_type": "ProductCouncilAnalysis",
        "content": {"some": "data"},
        "parent_id": "parent-id",
        "next_stage": "requirements",
        "existing": False
    }
    return orch

@pytest.mark.asyncio
async def test_execute_step_success(mock_orch):
    use_case = ExecuteWorkflowStepUseCase(mock_orch)
    result = await use_case.execute("proj-id", "model")

    assert result == {
        "artifact_id": "new-id",
        "artifact_type": "ProductCouncilAnalysis",
        "content": {"some": "data"},
        "parent_id": "parent-id",
        "next_stage": "requirements",
        "existing": False
    }
    mock_orch.get_next_step.assert_called_once_with("proj-id")
    mock_orch.execute_step.assert_called_once_with(
        "proj-id",
        mock_orch.get_next_step.return_value,
        "model"
    )

@pytest.mark.asyncio
async def test_execute_step_no_step(mock_orch):
    mock_orch.get_next_step.return_value = None
    use_case = ExecuteWorkflowStepUseCase(mock_orch)
    result = await use_case.execute("proj-id", None)

    assert result == {"error": "No next step"}
    mock_orch.execute_step.assert_not_called()

@pytest.mark.asyncio
async def test_execute_step_idea_stage(mock_orch):
    mock_orch.get_next_step.return_value = {
        "next_stage": "idea",
        "description": "Введите идею"
    }
    use_case = ExecuteWorkflowStepUseCase(mock_orch)
    result = await use_case.execute("proj-id", None)

    assert result == {"action": "input_idea", "description": "Введите идею"}
    mock_orch.execute_step.assert_not_called()

@pytest.mark.asyncio
async def test_execute_step_validation_error(mock_orch):
    mock_orch.execute_step.side_effect = ValidationError("Invalid")
    use_case = ExecuteWorkflowStepUseCase(mock_orch)
    with pytest.raises(ValidationError):
        await use_case.execute("proj-id", None)

@pytest.mark.asyncio
async def test_execute_step_generic_error(mock_orch):
    mock_orch.execute_step.side_effect = Exception("Something went wrong")
    use_case = ExecuteWorkflowStepUseCase(mock_orch)
    with pytest.raises(Exception, match="Something went wrong"):
        await use_case.execute("proj-id", None)
