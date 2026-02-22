import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workflow_engine import WorkflowEngine

@pytest.fixture
def mock_artifact_service():
    service = AsyncMock()
    service.generate_artifact = AsyncMock(return_value="new-artifact-id")
    return service

@pytest.mark.asyncio
async def test_get_default_workflow_id_found(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    mock_workflows = [
        {"id": "wf-1", "is_default": False},
        {"id": "wf-2", "is_default": True}
    ]
    with patch("workflow_engine.db.list_workflows", return_value=mock_workflows):
        result = await engine.get_default_workflow_id()
        assert result == "wf-2"

@pytest.mark.asyncio
async def test_get_default_workflow_id_not_found(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    mock_workflows = [{"id": "wf-1", "is_default": False}]
    with patch("workflow_engine.db.list_workflows", return_value=mock_workflows):
        result = await engine.get_default_workflow_id()
        assert result is None

@pytest.mark.asyncio
async def test_get_next_step_no_artifacts(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    with patch("workflow_engine.db.get_last_validated_artifact", return_value=None), \
         patch.object(engine, "get_default_workflow_id", return_value="default-id"):

        nodes = [
            {"node_id": "BusinessIdea", "prompt_key": "02_IDEA_CLARIFIER"},
            {"node_id": "ProductCouncilAnalysis", "prompt_key": "03_PRODUCT_COUNCIL"}
        ]
        edges = [{"source_node": "BusinessIdea", "target_node": "ProductCouncilAnalysis"}]
        with patch("workflow_engine.db.get_workflow_nodes", return_value=nodes), \
             patch("workflow_engine.db.get_workflow_edges", return_value=edges):

            step = await engine.get_next_step("proj-id")
            assert step is not None
            assert step["next_stage"] == "BusinessIdea"
            assert step["prompt_type"] == "02_IDEA_CLARIFIER"
            assert step["parent_id"] is None

@pytest.mark.asyncio
async def test_get_next_step_with_last_artifact(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    last_valid = {"id": "last-id", "type": "BusinessIdea"}
    with patch("workflow_engine.db.get_last_validated_artifact", return_value=last_valid), \
         patch.object(engine, "get_default_workflow_id", return_value="default-id"):

        nodes = [
            {"node_id": "BusinessIdea", "prompt_key": "02_IDEA_CLARIFIER"},
            {"node_id": "ProductCouncilAnalysis", "prompt_key": "03_PRODUCT_COUNCIL"}
        ]
        edges = [{"source_node": "BusinessIdea", "target_node": "ProductCouncilAnalysis"}]
        with patch("workflow_engine.db.get_workflow_nodes", return_value=nodes), \
             patch("workflow_engine.db.get_workflow_edges", return_value=edges):

            step = await engine.get_next_step("proj-id")
            assert step is not None
            assert step["next_stage"] == "ProductCouncilAnalysis"
            assert step["prompt_type"] == "03_PRODUCT_COUNCIL"
            assert step["parent_id"] == "last-id"

@pytest.mark.asyncio
async def test_get_next_step_finished(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    last_valid = {"id": "last-id", "type": "TestPackage"}
    with patch("workflow_engine.db.get_last_validated_artifact", return_value=last_valid), \
         patch.object(engine, "get_default_workflow_id", return_value="default-id"):

        nodes = [{"node_id": "TestPackage", "prompt_key": "11_TEST_GEN"}]
        edges = []
        with patch("workflow_engine.db.get_workflow_nodes", return_value=nodes), \
             patch("workflow_engine.db.get_workflow_edges", return_value=edges):

            step = await engine.get_next_step("proj-id")
            assert step is not None
            assert step["next_stage"] == "finished"
            assert step["parent_id"] == "last-id"

@pytest.mark.asyncio
async def test_get_next_step_type_not_in_workflow(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    last_valid = {"id": "last-id", "type": "UnknownType"}
    with patch("workflow_engine.db.get_last_validated_artifact", return_value=last_valid), \
         patch.object(engine, "get_default_workflow_id", return_value="default-id"):

        nodes = [{"node_id": "BusinessIdea", "prompt_key": "02_IDEA_CLARIFIER"}]
        edges = []
        with patch("workflow_engine.db.get_workflow_nodes", return_value=nodes), \
             patch("workflow_engine.db.get_workflow_edges", return_value=edges):

            step = await engine.get_next_step("proj-id")
            assert step is None

@pytest.mark.asyncio
async def test_execute_step_existing_artifact(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    step_info = {"prompt_type": "ProductCouncilAnalysis", "parent_id": "parent-id", "next_stage": "requirements"}
    existing = {
        "id": "existing-id",
        "status": "VALIDATED",
        "content": {"some": "data"}
    }
    with patch("workflow_engine.db.get_last_version_by_parent_and_type", return_value=existing):
        result = await engine.execute_step("proj-id", step_info, model="model")
        assert result["artifact_id"] == "existing-id"
        assert result["artifact_type"] == "ProductCouncilAnalysis"
        assert result["content"] == {"some": "data"}
        assert result["parent_id"] == "parent-id"
        assert result["next_stage"] == "requirements"
        assert result["existing"] is True
        mock_artifact_service.generate_artifact.assert_not_called()

@pytest.mark.asyncio
async def test_execute_step_new_artifact(mock_artifact_service):
    engine = WorkflowEngine(mock_artifact_service)
    step_info = {"prompt_type": "ProductCouncilAnalysis", "parent_id": "parent-id", "next_stage": "requirements"}

    # Side effect для двух вызовов db.get_artifact
    async def get_artifact_side_effect(artifact_id, conn=None):
        if artifact_id == "parent-id":
            return {"id": "parent-id", "content": {}}
        elif artifact_id == "new-artifact-id":
            return {"id": "new-artifact-id", "content": {"result": "ok"}}
        return None

    with patch("workflow_engine.db.get_last_version_by_parent_and_type", return_value=None), \
         patch("workflow_engine.db.get_artifact", side_effect=get_artifact_side_effect):

        result = await engine.execute_step("proj-id", step_info, model="model")
        assert result["artifact_id"] == "new-artifact-id"
        assert result["artifact_type"] == "ProductCouncilAnalysis"
        assert result["content"] == {"result": "ok"}
        assert result["existing"] is False
        mock_artifact_service.generate_artifact.assert_called_once_with(
            artifact_type="ProductCouncilAnalysis",
            user_input="",
            parent_artifact={"id": "parent-id", "content": {}},
            model_id="model",
            project_id="proj-id"
        )
