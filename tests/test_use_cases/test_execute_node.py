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
    mock.find_last_attempt_by_base_key = AsyncMock()          # FIXED: was find_existing_execution
    mock.create_node_execution = AsyncMock()
    mock.get_node_execution = AsyncMock()  # for after creation
    mock.update_node_execution_status = AsyncMock()
    mock.create_retry_attempt = AsyncMock()
    return mock

@pytest.fixture
def mock_queue_repo(mocker):                                  # ADDED
    mock = mocker.patch('use_cases.execute_node.execution_queue_repository')
    mock.enqueue = AsyncMock()
    return mock

@pytest.fixture
def mock_artifact_service():
    mock = AsyncMock()
    mock.generate_artifact = AsyncMock()
    return mock

@pytest.fixture
def mock_background_tasks(mocker):
    return MagicMock(spec=['add_task'])

@pytest.fixture
def mock_transaction(mocker):
    """Provides a mocked transaction context manager with an accessible transaction object."""
    mock_tx = AsyncMock()
    mock_tx.conn = AsyncMock()
    mock_tx.conn.fetchrow = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_tx)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    mocker.patch('use_cases.execute_node.transaction', return_value=mock_ctx)
    mock_ctx.tx = mock_tx
    return mock_ctx

@pytest.fixture
def use_case(mock_artifact_service):
    return ExecuteNodeUseCase(mock_artifact_service)

# ----------------------------------------------------------------------
# Helper to create dummy execution dict (as returned by repository)
# ----------------------------------------------------------------------
def dummy_execution(exec_id=None, status="PROCESSING", parent_id=None, output_id=None,
                    attempt=1, max_attempts=3, base_idempotency_key="base"):
    return {
        "id": exec_id or str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "node_definition_id": str(uuid.uuid4()),
        "parent_execution_id": parent_id,
        "status": status,
        "input_artifact_ids": [],
        "output_artifact_id": output_id,
        "idempotency_key": "dummy",
        "base_idempotency_key": base_idempotency_key,
        "attempt": attempt,
        "max_attempts": max_attempts,
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
    mock_queue_repo,                                            # ADDED
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
    workflow_id = str(uuid.uuid4())

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": project_id,
        "workflow_id": workflow_id
    }

    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "config": {}
    }
    mock_node_exec_repo.find_last_attempt_by_base_key.return_value = None   # FIXED
    new_exec_id = str(uuid.uuid4())
    mock_node_exec_repo.create_node_execution.return_value = new_exec_id
    mock_node_exec_repo.get_node_execution.side_effect = [
        dummy_execution(exec_id=new_exec_id)
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

    mock_transaction.tx.conn.fetchrow.assert_awaited_once_with(
        "SELECT * FROM runs WHERE id = $1 FOR UPDATE", run_id
    )
    mock_workflow_repo.get_workflow_node_by_id.assert_awaited_once_with(node_id)
    mock_node_exec_repo.find_last_attempt_by_base_key.assert_awaited_once_with(   # FIXED
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=parent_id,
        base_idempotency_key=idempotency_key,
        tx=mock_transaction.tx
    )
    mock_node_exec_repo.create_node_execution.assert_awaited_once_with(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=parent_id,
        idempotency_key=idempotency_key,
        input_artifact_ids=input_artifact_ids,
        attempt=1,
        max_attempts=3,
        retry_parent_id=None,
        tx=mock_transaction.tx
    )
    mock_queue_repo.enqueue.assert_awaited_once_with(new_exec_id, tx=mock_transaction.tx)   # ADDED
    mock_node_exec_repo.get_node_execution.assert_awaited_with(new_exec_id, tx=mock_transaction.tx)
    assert result["id"] == new_exec_id
    assert result["status"] == "PROCESSING"

@pytest.mark.asyncio
async def test_execute_existing_execution(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_queue_repo,                                            # ADDED (though not used here)
    mock_background_tasks,
    mock_transaction
):
    run_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    existing_exec = dummy_execution(status="COMPLETED")
    workflow_id = str(uuid.uuid4())

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": "proj",
        "workflow_id": workflow_id
    }

    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "config": {}
    }
    mock_node_exec_repo.find_last_attempt_by_base_key.return_value = existing_exec   # FIXED

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
    mock_queue_repo.enqueue.assert_not_called()                 # ADDED

@pytest.mark.asyncio
async def test_execute_run_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = "missing"
    node_id = "node"

    mock_transaction.tx.conn.fetchrow.return_value = None

    with pytest.raises(ValueError, match="Run .* not found"):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
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
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = "r"
    node_id = "node"

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "FROZEN",
        "project_id": "proj",
        "workflow_id": "wf"
    }

    with pytest.raises(ValueError, match="Run .* is not OPEN"):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
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
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = "r"
    node_id = "missing"

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": "proj",
        "workflow_id": "wf"
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = None

    with pytest.raises(ValueError, match="Node .* not found"):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
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
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = "r"
    node_id = "node"

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "workflow_id": "wf1"
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": "wf2"
    }

    with pytest.raises(ValueError, match="Node does not belong to workflow"):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
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
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = "r"
    node_id = "node"
    parent_id = str(uuid.uuid4())

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": "proj",
        "workflow_id": "wf"
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": "wf"
    }
    mock_node_exec_repo.get_node_execution.return_value = None

    with pytest.raises(ValueError, match="Parent execution .* not found"):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
            parent_execution_id=parent_id,
            idempotency_key="key",
            input_artifact_ids=[],
            model=None,
            background_tasks=mock_background_tasks
        )

    mock_node_exec_repo.get_node_execution.assert_awaited_once_with(parent_id, tx=mock_transaction.tx)

@pytest.mark.asyncio
async def test_execute_parent_invalid_status(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction
):
    run_id = "r"
    node_id = "node"
    parent_id = str(uuid.uuid4())

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": "proj",
        "workflow_id": "wf"
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": "wf"
    }
    mock_node_exec_repo.get_node_execution.return_value = {
        "id": parent_id,
        "status": "FAILED"
    }

    with pytest.raises(ValueError, match="Parent status must be COMPLETED or VALIDATED"):
        await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
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
    mock_queue_repo,
    mock_background_tasks,
    mock_transaction,
    mocker
):
    """Simulate a UniqueViolationError when creating node execution."""
    run_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())

    mock_transaction.tx.conn.fetchrow.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": "proj",
        "workflow_id": workflow_id
    }

    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "config": {}
    }
    mock_node_exec_repo.find_last_attempt_by_base_key.return_value = None   # FIXED

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
# Tests for background completion (now obsolete – moved to worker)
# ----------------------------------------------------------------------

@pytest.mark.skip(reason="Functionality moved to worker (queue processing)")
@pytest.mark.asyncio
async def test_complete_execution_success():
    pass

@pytest.mark.skip(reason="Functionality moved to worker (queue processing)")
@pytest.mark.asyncio
async def test_complete_execution_node_not_found():
    pass

@pytest.mark.skip(reason="Functionality moved to worker (queue processing)")
@pytest.mark.asyncio
async def test_complete_execution_generation_fails():
    pass

@pytest.mark.skip(reason="Functionality moved to worker (queue processing)")
@pytest.mark.asyncio
async def test_complete_execution_other_error():
    pass