# ADDED: Execute workflow step use case
import logging
from typing import Optional
from orchestrator import MrakOrchestrator
from validation import ValidationError

logger = logging.getLogger(__name__)

class ExecuteWorkflowStepUseCase:
    def __init__(self, orch: MrakOrchestrator):
        self.orch = orch

    async def execute(self, project_id: str, model: Optional[str] = None):
        step = await self.orch.get_next_step(project_id)
        if not step:
            return {"error": "No next step"}
        if step['next_stage'] == 'idea':
            return {"action": "input_idea", "description": step['description']}

        result = await self.orch.execute_step(project_id, step, model)
        return result
