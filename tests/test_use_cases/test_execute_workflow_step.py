"""
Unit tests for ExecuteWorkflowStepUseCase.
All external dependencies are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call, ANY
import uuid
from uuid import uuid4

from use_cases.execute_workflow_step import ExecuteWorkflowStepUseCase
from schemas import ExecuteStepRequest

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def mock_run_repo(mocker):
    mock = mocker.patch('use_cases.execute_workflow_step.run_repository')
    mock.get_run = AsyncMock()
    mock.list_runs = AsyncMock(return_value=[])
    mock.create_run = AsyncMock()
    return mock

@pytest.fixture
def mock_workflow_repo(mocker):
    mock = mocker.patch('use_cases.execute_workflow_step.workflow_repository')
    mock.get_workflow_node_by_id = AsyncMock()
    return mock

@pytest.fixture
def mock_node_exec_repo(mocker):
    mock = mocker.patch('use_cases.execute_workflow_step.node_execution_repository')
    mock.find_existing_execution = AsyncMock(return_value=None)
    mock.create_node_execution = AsyncMock()
    mock.get_node_execution = AsyncMock()
    mock.update_node_execution_status = AsyncMock()
    return mock

@pytest.fixture
def mock_artifact_repo(mocker):
    mock = mocker.patch('use_cases.execute_workflow_step.artifact_repository')
    mock.get_artifact = AsyncMock()
    mock.get_artifacts_by_ids = AsyncMock(return_value=[])
    mock.update_artifact_node_execution = AsyncMock()
    return mock

@pytest.fixture
def mock_artifact_service(mocker):
    mock = AsyncMock()
    mock.generate_artifact = AsyncMock()
    return mock

@pytest.fixture
def mock_transaction(mocker):
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mocker.patch('use_cases.execute_workflow_step.transaction', return_value=mock_ctx)
    return mock_ctx

@pytest.fixture
def use_case(mock_artifact_service):
    return ExecuteWorkflowStepUseCase(mock_artifact_service)

# ----------------------------------------------------------------------
# Helper to create a dummy execution dict
# ----------------------------------------------------------------------
def dummy_execution(exec_id=None, status="PROCESSING", output_id=None):
    return {
        "id": exec_id or str(uuid4()),
        "run_id": str(uuid4()),
        "node_definition_id": str(uuid4()),
        "status": status,
        "output_artifact_id": output_id,
    }

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_step_new_execution(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    run_id = str(uuid4())
    node_id = str(uuid4())
    project_id = str(uuid4())
    workflow_id = str(uuid4())

    mock_run_repo.get_run.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": project_id,
        "workflow_id": workflow_id
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "node_id": "test_node",
        "config": {
            "system_prompt": "test",
            "user_prompt_template": "template"
        }
    }
    mock_node_exec_repo.find_existing_execution.return_value = None
    exec_id = str(uuid4())
    mock_node_exec_repo.create_node_execution.return_value = exec_id
    mock_node_exec_repo.get_node_execution.side_effect = [
        dummy_execution(exec_id=exec_id, status="PROCESSING"),
        dummy_execution(exec_id=exec_id, status="COMPLETED", output_id="art-1")
    ]
    artifact_id = str(uuid4())
    mock_artifact_service.generate_artifact.return_value = artifact_id
    mock_artifact_repo.get_artifact.return_value = {"id": artifact_id, "content": {"result": "ok"}}

    req = ExecuteStepRequest(
        node_id=node_id,
        run_id=run_id,
        idempotency_key="key123",
        parent_execution_id=None,
        input_artifact_ids=["art-in-1"],
        feedback="feedback",
        model="model"
    )

    result = await use_case.execute(req)

    # Проверяем, что get_workflow_node_by_id вызван один раз (после run)
    mock_workflow_repo.get_workflow_node_by_id.assert_called_once_with(node_id)

    mock_node_exec_repo.find_existing_execution.assert_awaited_once_with(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=None,
        idempotency_key="key123"
    )
    mock_node_exec_repo.create_node_execution.assert_awaited_once_with(
        run_id=run_id,
        node_definition_id=node_id,
        parent_execution_id=None,
        idempotency_key="key123",
        input_artifact_ids=["art-in-1"],
        tx=mocker.ANY
    )
    mock_artifact_service.generate_artifact.assert_awaited_once_with(
        artifact_type="test_node",
        input_artifacts=[],
        user_input="feedback",
        model_id="model",
        project_id=project_id,
        generation_config={
            "system_prompt": "test",
            "user_prompt_template": "template",
            "required_input_types": []
        }
    )
    mock_node_exec_repo.update_node_execution_status.assert_awaited_once_with(
        exec_id=exec_id,
        status="COMPLETED",
        output_artifact_id=artifact_id,
        tx=mocker.ANY
    )
    assert result["execution"]["id"] == exec_id
    assert result["execution"]["status"] == "COMPLETED"
    assert result["artifact"]["id"] == artifact_id
    assert result["existing"] is False

@pytest.mark.asyncio
async def test_execute_step_existing_execution(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    run_id = str(uuid4())
    node_id = str(uuid4())
    project_id = str(uuid4())
    workflow_id = str(uuid4())
    existing_exec = dummy_execution(exec_id="exec-1", status="COMPLETED", output_id="art-1")

    mock_run_repo.get_run.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": project_id,
        "workflow_id": workflow_id
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "node_id": "test_node",
        "config": {}
    }
    mock_node_exec_repo.find_existing_execution.return_value = existing_exec
    mock_artifact_repo.get_artifact.return_value = {"id": "art-1", "content": "data"}

    req = ExecuteStepRequest(
        node_id=node_id,
        run_id=run_id,
        idempotency_key="key123",
        parent_execution_id=None,
        input_artifact_ids=[],
        feedback="",
        model=None
    )

    result = await use_case.execute(req)

    mock_workflow_repo.get_workflow_node_by_id.assert_called_once_with(node_id)
    mock_node_exec_repo.find_existing_execution.assert_awaited_once()
    mock_artifact_repo.get_artifact.assert_awaited_once_with("art-1")
    mock_node_exec_repo.create_node_execution.assert_not_called()
    mock_artifact_service.generate_artifact.assert_not_called()
    assert result["execution"] == existing_exec
    assert result["artifact"] == {"id": "art-1", "content": "data"}
    assert result["existing"] is True

@pytest.mark.asyncio
async def test_execute_step_no_run_id_auto_create(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    node_id = str(uuid4())
    project_id = str(uuid4())
    workflow_id = str(uuid4())

    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "project_id": project_id,
        "node_id": "test_node",
        "config": {}
    }
    mock_run_repo.list_runs.return_value = []
    new_run_id = str(uuid4())
    mock_run_repo.create_run.return_value = new_run_id
    mock_run_repo.get_run.return_value = {
        "id": new_run_id,
        "status": "OPEN",
        "project_id": project_id,
        "workflow_id": workflow_id
    }

    mock_node_exec_repo.find_existing_execution.return_value = None
    exec_id = str(uuid4())
    mock_node_exec_repo.create_node_execution.return_value = exec_id
    mock_node_exec_repo.get_node_execution.side_effect = [
        dummy_execution(exec_id=exec_id, status="PROCESSING"),
        dummy_execution(exec_id=exec_id, status="COMPLETED", output_id="art-1")
    ]
    artifact_id = str(uuid4())
    mock_artifact_service.generate_artifact.return_value = artifact_id
    mock_artifact_repo.get_artifact.return_value = {"id": artifact_id, "content": {"ok": True}}

    req = ExecuteStepRequest(
        node_id=node_id,
        run_id=None,
        idempotency_key=None,
        parent_execution_id=None,
        input_artifact_ids=[],
        feedback="",
        model=None
    )

    result = await use_case.execute(req)

    # При отсутствии run_id первый вызов get_workflow_node_by_id происходит в блоке else,
    # затем после создания run второй вызов для конфигурации.
    assert mock_workflow_repo.get_workflow_node_by_id.call_count == 2
    mock_run_repo.list_runs.assert_awaited_once_with(project_id=project_id)
    mock_run_repo.create_run.assert_awaited_once_with(project_id, workflow_id, created_by="system")
    assert mock_node_exec_repo.create_node_execution.call_args[1]["idempotency_key"] is not None
    assert result["execution"]["id"] == exec_id
    assert result["existing"] is False

@pytest.mark.asyncio
async def test_execute_step_run_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo
):
    mock_run_repo.get_run.return_value = None
    req = ExecuteStepRequest(
        node_id=str(uuid4()),
        run_id=str(uuid4()),
        idempotency_key="k",
        parent_execution_id=None,
        input_artifact_ids=[],
        feedback="",
        model=None
    )
    with pytest.raises(ValueError, match="Run .* not found"):
        await use_case.execute(req)

@pytest.mark.asyncio
async def test_execute_step_run_not_open(
    use_case,
    mock_run_repo,
    mock_workflow_repo
):
    run_id = str(uuid4())
    mock_run_repo.get_run.return_value = {"id": run_id, "status": "FROZEN"}
    req = ExecuteStepRequest(
        node_id=str(uuid4()),
        run_id=run_id,
        idempotency_key="k",
        parent_execution_id=None,
        input_artifact_ids=[],
        feedback="",
        model=None
    )
    with pytest.raises(ValueError, match="Run .* is not OPEN"):
        await use_case.execute(req)

@pytest.mark.asyncio
async def test_execute_step_node_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo
):
    run_id = str(uuid4())
    mock_run_repo.get_run.return_value = {"id": run_id, "status": "OPEN"}
    mock_workflow_repo.get_workflow_node_by_id.return_value = None
    req = ExecuteStepRequest(
        node_id=str(uuid4()),
        run_id=run_id,
        idempotency_key="k",
        parent_execution_id=None,
        input_artifact_ids=[],
        feedback="",
        model=None
    )
    with pytest.raises(ValueError, match="Node .* not found"):
        await use_case.execute(req)

@pytest.mark.asyncio
async def test_execute_step_parent_not_found(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_service
):
    run_id = str(uuid4())
    node_id = str(uuid4())
    parent_id = str(uuid4())

    # Настройка моков только для необходимых вызовов
    mock_run_repo.get_run.return_value = {
        "id": run_id,
        "status": "OPEN",
        "workflow_id": "wf",
        "project_id": "proj-id"
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": "wf",
        "config": {}
    }
    mock_node_exec_repo.get_node_execution.return_value = None

    req = ExecuteStepRequest(
        node_id=node_id,
        run_id=run_id,
        idempotency_key="k",
        parent_execution_id=parent_id,
        input_artifact_ids=[],
        feedback="",
        model=None
    )

    with pytest.raises(ValueError, match="Parent execution .* not found"):
        await use_case.execute(req)

    # Проверяем, что get_node_execution был вызван с правильным ID
    mock_node_exec_repo.get_node_execution.assert_awaited_once_with(parent_id)
    # Убеждаемся, что создание нового выполнения и генерация не вызывались
    mock_node_exec_repo.create_node_execution.assert_not_called()
    mock_node_exec_repo.update_node_execution_status.assert_not_called()
    mock_artifact_service.generate_artifact.assert_not_called()

@pytest.mark.asyncio
async def test_execute_step_generation_fails(
    use_case,
    mock_run_repo,
    mock_workflow_repo,
    mock_node_exec_repo,
    mock_artifact_service,
    mock_transaction,
    mocker
):
    run_id = str(uuid4())
    node_id = str(uuid4())
    project_id = str(uuid4())
    workflow_id = str(uuid4())

    mock_run_repo.get_run.return_value = {
        "id": run_id,
        "status": "OPEN",
        "project_id": project_id,
        "workflow_id": workflow_id
    }
    mock_workflow_repo.get_workflow_node_by_id.return_value = {
        "id": node_id,
        "workflow_id": workflow_id,
        "node_id": "test_node",
        "config": {}
    }
    mock_node_exec_repo.find_existing_execution.return_value = None
    exec_id = str(uuid4())
    mock_node_exec_repo.create_node_execution.return_value = exec_id
    mock_node_exec_repo.get_node_execution.side_effect = [
        dummy_execution(exec_id=exec_id, status="PROCESSING"),
        dummy_execution(exec_id=exec_id, status="FAILED")
    ]
    mock_artifact_service.generate_artifact.side_effect = Exception("LLM error")

    req = ExecuteStepRequest(
        node_id=node_id,
        run_id=run_id,
        idempotency_key="key",
        parent_execution_id=None,
        input_artifact_ids=[],
        feedback="",
        model=None
    )

    with pytest.raises(Exception, match="LLM error"):
        await use_case.execute(req)

    mock_node_exec_repo.update_node_execution_status.assert_awaited_once_with(
        exec_id=exec_id,
        status="FAILED",
        tx=mocker.ANY
    )
