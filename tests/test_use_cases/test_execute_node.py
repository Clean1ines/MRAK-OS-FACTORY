# tests/test_use_cases/test_execute_node.py
"""
Unit tests for ExecuteNodeUseCase with proper async mocks.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call
import uuid

from use_cases.execute_node import ExecuteNodeUseCase

# ----------------------------------------------------------------------
# Fixtures for common mocks
# ----------------------------------------------------------------------

@pytest.fixture
def mock_run_repo(mocker):
    mock = mocker.patch('use_cases.execute_node.run_repository')
    mock.get_run = AsyncMock()
    return mock

@pytest.fixture
def mock_workflow_repo(mocker):
    mock = mocker.patch('use_cases.execute_node.workflow_repository')
    mock.get_workflow_node_by_id = AsyncMock()
    return mock

@pytest.fixture
def mock_node_exec_repo(mocker):
    mock = mocker.patch('use_cases.execute_node.node_execution_repository')
    mock.get_node_execution = AsyncMock()
    mock.find_existing_execution = AsyncMock()
    mock.create_node_execution = AsyncMock()
    mock.get_node_execution = AsyncMock()  # for after creation
    mock.update_node_execution_status = AsyncMock()
    return mock

@pytest.fixture
def mock_artifact_repo(mocker):
    mock = mocker.patch('use_cases.execute_node.artifact_repository')
    mock.get_artifacts_by_ids = AsyncMock()
    return mock

@pytest.fixture
def mock_artifact_service():
    # Create AsyncMock without spec to avoid attribute issues
    mock = AsyncMock()
    mock.generate_artifact = AsyncMock()
    return mock

@pytest.fixture
def mock_background_tasks(mocker):
    return MagicMock(spec=['add_task'])

@pytest.fixture
def mock_transaction(mocker):
    # Mock the transaction context manager so it returns an async context manager
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock())  # return a dummy tx object
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mocker.patch('use_cases.execute_node.transaction', return_value=mock_ctx)
    return mock_ctx  # this is the context manager, not the tx object

@pytest.fixture
def use_case(mock_artifact_service):
    return ExecuteNodeUseCase(mock_artifact_service)

# ----------------------------------------------------------------------
# Helper to create dummy execution dict (as returned by repository)
# ----------------------------------------------------------------------
def dummy_execution(exec_id=None, status="PROCESSING", parent_id=None, output_id=None):
    return {
        "id": exec_id or str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "node_definition_id": str(uuid.uuid4()),
        "parent_execution_id": parent_id,
        "status": status,
        "input_artifact_ids": [],
        "output_artifact_id": output_id,
        "idempotency_key": "dummy",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00"
    }

# ----------------------------------------------------------------------
# Tests for execute()
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_new_execution_success(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks,
    mock_transaction,
    mocker
):
    run_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    parent_id = None
    idempotency_key = "key123"
    input_artifact_ids = ["art1", "art2"]
    model = "test-model"
    project_id = str(uuid.uuid4())

    mock_run_repo.get_run.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": project_id,
        "workflow_id": str(uuid.uuid4())
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": mock_run_repo.get_run.return_value["workflow_id"],
        "config": {}
    }
    mock_node_exec_repo.find_existing_execution.return_value = None
    new_exec_id = str(uuid.uuid4())
    mock_node_exec_repo.create_node_execution.return_value = new_exec_id
    mock_node_exec_repo.get_node_execution.side_effect = [
        dummy_execution(exec_id=new_exec_id)  # for the return after creation
    ]

    result = await use_case.execute(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=parent_id,
        idempotency_key=idempotency_key,
        input_artifact_ids=input_artifact_ids,
        model=model,
        background_tasks=mock_background_tasks
    )

    mock_run_repo.get_run.assert_awaited_once_with(run_id)
    mock_workflow_repo.get_workflow_node_by_id.assert_awaited_once_with(node_id)
    mock_node_exec_repo.find_existing_execution.assert_awaited_once_with(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=parent_id,
        idempotency_key=idempotency_key
    )
    mock_node_exec_repo.create_node_execution.assert_awaited_once_with(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=parent_id,
        idempotency_key=idempotency_key,
        input_artifact_ids=input_artifact_ids,
        tx=mocker.ANY
    )
    mock_node_exec_repo.get_node_execution.assert_awaited_with(new_exec_id, tx=mocker.ANY)

    # Verify background task was scheduled with correct kwargs
    mock_background_tasks.add_task.assert_called_once()
    call_args = mock_background_tasks.add_task.call_args
    args, kwargs = call_args
    assert args[0] == use_case._complete_execution
    assert kwargs['exec_id'] == new_exec_id
    assert kwargs['node_definition_id'] == node_id
    assert kwargs['project_id'] == project_id
    assert kwargs['model'] == model
    assert kwargs['input_artifact_ids'] == input_artifact_ids

    assert result["id"] == new_exec_id
    assert result["status"] == "PROCESSING"

@pytest.mark.asyncio
async def test_execute_existing_execution(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    existing_exec = dummy_execution(status="COMPLETED")

    mock_run_repo.get_run.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": "proj",
        "workflow_id": "wf"
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": "wf",
        "config": {}
    }
    mock_node_exec_repo.find_existing_execution.return_value = existing_exec

    result = await use_case.execute(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=None,
        idempotency_key="key",
        input_artifact_ids=[],
        model=None,
        background_tasks=mock_background_tasks
    )

    assert result == existing_exec
    mock_node_exec_repo.create_node_execution.assert_not_called()
    mock_background_tasks.add_task.assert_not_called()

@pytest.mark.asyncio
async def test_execute_run_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks
):
    mock_run_repo.get_run.return_value = None
    with pytest.raises(ValueError, match="Run .* not found"):
        await use_case.execute(
            run_id="missing",
            node_definition_id="node",
            parent_execution_id=None,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

@pytest.mark.asyncio
async def test_execute_run_not_open(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks
):
    mock_run_repo.get_run.return_value = {"id": "r", "status": "FROZEN"}
    with pytest.raises(ValueError, match="Run .* is not OPEN"):
        await use_case.execute(
            run_id="r",
            node_definition_id="node",
            parent_execution_id=None,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

@pytest.mark.asyncio
async def test_execute_node_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks
):
    mock_run_repo.get_run.return_value = {"id": "r", "status": "OPEN"}
    mock_workflow_repo.get_workflow_node_by_id.return_value = None
    with pytest.raises(ValueError, match="Node .* not found"):
        await use_case.execute(
            run_id="r",
            node_definition_id="missing",
            parent_execution_id=None,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

@pytest.mark.asyncio
async def test_execute_node_workflow_mismatch(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks
):
    mock_run_repo.get_run.return_value = {"id": "r", "status": "OPEN", "workflow_id": "wf1"}
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": "node",
        "workflow_id": "wf2"
    }
    with pytest.raises(ValueError, match="Node does not belong to workflow"):
        await use_case.execute(
            run_id="r",
            node_definition_id="node",
            parent_execution_id=None,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

@pytest.mark.asyncio
async def test_execute_parent_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks
):
    mock_run_repo.get_run.return_value = {"id": "r", "status": "OPEN", "workflow_id": "wf"}
    mock_workflow_repo.get_workflow_node_by_id.return_value = {"id": "node", "workflow_id": "wf"}
    mock_node_exec_repo.get_node_execution.return_value = None
    parent_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Parent execution .* not found"):
        await use_case.execute(
            run_id="r",
            node_definition_id="node",
            parent_execution_id=parent_id,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )
    # Real call does not pass tx=None
    mock_node_exec_repo.get_node_execution.assert_awaited_once_with(parent_id)

@pytest.mark.asyncio
async def test_execute_parent_invalid_status(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks
):
    mock_run_repo.get_run.return_value = {"id": "r", "status": "OPEN", "workflow_id": "wf"}
    mock_workflow_repo.get_workflow_node_by_id.return_value = {"id": "node", "workflow_id": "wf"}
    parent_id = str(uuid.uuid4())
    mock_node_exec_repo.get_node_execution.return_value = {
        "id": parent_id,
        "status": "FAILED"
    }
    with pytest.raises(ValueError, match="Parent status must be COMPLETED or VALIDATED"):
        await use_case.execute(
            run_id="r",
            node_definition_id="node",
            parent_execution_id=parent_id,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

@pytest.mark.asyncio
async def test_execute_unique_violation(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_background_tasks,
    mock_transaction,
    mocker
):
    """Simulate a UniqueViolationError when creating node execution."""
    run_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    mock_run_repo.get_run.return_value = {"id": run_id, "status": "OPEN", "project_id": "proj", "workflow_id": "wf"}
    mock_workflow_repo.get_workflow_node_by_id.return_value = {"id": node_id, "workflow_id": "wf", "config": {}}
    mock_node_exec_repo.find_existing_execution.return_value = None

    from asyncpg.exceptions import UniqueViolationError
    mock_node_exec_repo.create_node_execution.side_effect = UniqueViolationError()

    with pytest.raises(UniqueViolationError):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
            parent_execution_id=None,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

# ----------------------------------------------------------------------
# Tests for _complete_execution (background task)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_execution_success(
    use_case,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    exec_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    model = "test"
    input_artifact_ids = ["art1", "art2"]
    artifact_type = "test_node"
    system_prompt = "You are a helpful assistant."
    template = "Context: {all_artifacts}\nUser: {user_input}"
    node_config = {
        "system_prompt": system_prompt,
        "user_prompt_template": template,
        "required_input_types": []
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "node_id": artifact_type,
        "config": node_config
    }
    mock_artifact_repo.get_artifacts_by_ids.return_value = [{"id": "art1", "type": "test"}]
    artifact_id = str(uuid.uuid4())
    mock_artifact_service.generate_artifact.return_value = artifact_id

    await use_case._complete_execution(
        exec_id=exec_id,
        node_definition_id=node_id,
        project_id=project_id,
        model=model,
        input_artifact_ids=input_artifact_ids
    )

    mock_workflow_repo.get_workflow_node_by_id.assert_awaited_once_with(node_id)
    mock_artifact_repo.get_artifacts_by_ids.assert_awaited_once_with(input_artifact_ids)
    mock_artifact_service.generate_artifact.assert_awaited_once_with(
        artifact_type=artifact_type,
        input_artifacts=[{"id": "art1", "type": "test"}],
        user_input="",
        model_id=model,
        project_id=project_id,
        generation_config={
            'system_prompt': system_prompt,
            'user_prompt_template': template,
            'required_input_types': []
        }
    )
    # We cannot know the exact tx object, so use ANY
    mock_node_exec_repo.update_node_execution_status.assert_awaited_once_with(
        exec_id=exec_id,
        status="COMPLETED",
        output_artifact_id=artifact_id,
        tx=mocker.ANY
    )

@pytest.mark.asyncio
async def test_complete_execution_node_not_found(
    use_case,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    exec_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    mock_workflow_repo.get_workflow_node_by_id.return_value = None

    await use_case._complete_execution(
        exec_id=exec_id,
        node_definition_id=node_id,
        project_id="proj",
        model=None,
        input_artifact_ids=[]
    )

    # Should catch exception and set status to FAILED
    mock_node_exec_repo.update_node_execution_status.assert_awaited_once_with(
        exec_id=exec_id,
        status="FAILED",
        tx=mocker.ANY
    )
    mock_artifact_repo.get_artifacts_by_ids.assert_not_called()
    mock_artifact_service.generate_artifact.assert_not_called()

@pytest.mark.asyncio
async def test_complete_execution_generation_fails(
    use_case,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    exec_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    input_artifact_ids = ["art1"]
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "node_id": "type",
        "config": {}
    }
    mock_artifact_repo.get_artifacts_by_ids.return_value = []
    mock_artifact_service.generate_artifact.side_effect = Exception("LLM failed")

    await use_case._complete_execution(
        exec_id=exec_id,
        node_definition_id=node_id,
        project_id=project_id,
        model=None,
        input_artifact_ids=input_artifact_ids
    )

    mock_node_exec_repo.update_node_execution_status.assert_awaited_once_with(
        exec_id=exec_id,
        status="FAILED",
        tx=mocker.ANY
    )

@pytest.mark.asyncio
async def test_complete_execution_other_error(
    use_case,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    exec_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "node_id": "type",
        "config": {}
    }
    mock_artifact_repo.get_artifacts_by_ids.side_effect = RuntimeError("DB error")

    await use_case._complete_execution(
        exec_id=exec_id,
        node_definition_id=node_id,
        project_id="proj",
        model=None,
        input_artifact_ids=["art1"]
    )

    mock_node_exec_repo.update_node_execution_status.assert_awaited_once_with(
        exec_id=exec_id,
        status="FAILED",
        tx=mocker.ANY
    )