import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from orchestrator import MrakOrchestrator

@pytest.fixture
def mock_services():
    with patch("orchestrator.PromptService") as MockPrompt, \
         patch("orchestrator.ArtifactService") as MockArtifact, \
         patch("orchestrator.WorkflowEngine") as MockWorkflow:

        mock_prompt = MockPrompt.return_value
        mock_prompt.get_system_prompt = AsyncMock()
        mock_prompt.get_chat_completion = AsyncMock()
        mock_prompt.synthesize_conversation_state = AsyncMock()

        mock_artifact = MockArtifact.return_value
        mock_artifact.generate_artifact = AsyncMock()
        mock_artifact.generate_business_requirements = AsyncMock()
        mock_artifact.generate_req_engineering_analysis = AsyncMock()
        mock_artifact.generate_functional_requirements = AsyncMock()

        yield {
            "prompt": mock_prompt,
            "artifact": mock_artifact,
            "workflow": MockWorkflow.return_value
        }

@pytest.fixture
def orchestrator(mock_services):
    with patch("orchestrator.GroqClient"), patch("orchestrator.PromptLoader"):
        orch = MrakOrchestrator()
        orch.prompt_service = mock_services["prompt"]
        orch.artifact_service = mock_services["artifact"]
        orch.workflow_engine = mock_services["workflow"]
        return orch

@pytest.mark.asyncio
async def test_get_system_prompt_delegation(orchestrator, mock_services):
    await orchestrator.get_system_prompt("mode")
    mock_services["prompt"].get_system_prompt.assert_called_once_with("mode")

@pytest.mark.asyncio
async def test_get_chat_completion_delegation(orchestrator, mock_services):
    messages = [{"role": "user", "content": "hi"}]
    await orchestrator.get_chat_completion(messages, "model")
    mock_services["prompt"].get_chat_completion.assert_called_once_with(messages, "model")

@pytest.mark.asyncio
async def test_synthesize_conversation_state_delegation(orchestrator, mock_services):
    history = []
    await orchestrator.synthesize_conversation_state(history, "model")
    mock_services["prompt"].synthesize_conversation_state.assert_called_once_with(history, "model")

@pytest.mark.asyncio
async def test_generate_artifact_delegation(orchestrator, mock_services):
    await orchestrator.generate_artifact("type", "input", None, "model", "proj")
    mock_services["artifact"].generate_artifact.assert_called_once_with("type", "input", None, "model", "proj")

@pytest.mark.asyncio
async def test_generate_business_requirements_delegation(orchestrator, mock_services):
    await orchestrator.generate_business_requirements("analysis-id", "feedback")
    mock_services["artifact"].generate_business_requirements.assert_called_once_with(
        analysis_id="analysis-id",
        user_feedback="feedback",
        model_id=None,
        project_id=None,
        existing_requirements=None
    )
