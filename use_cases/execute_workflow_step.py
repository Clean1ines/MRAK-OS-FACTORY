# CHANGED: Use workflow_engine instead of orchestrator
import logging
from typing import Optional
from workflow_engine import WorkflowEngine
from validation import ValidationError

logger = logging.getLogger(__name__)

class ExecuteWorkflowStepUseCase:
    def __init__(self, workflow_engine: WorkflowEngine):
        self.workflow_engine = workflow_engine

    async def execute(self, project_id: str, model: Optional[str] = None):
        step = await self.workflow_engine.get_next_step(project_id)
        if not step:
            return {"error": "No next step"}
        if step['next_stage'] == 'idea':
            return {"action": "input_idea", "description": step['description']}

        result = await self.workflow_engine.execute_step(project_id, step, model)
        return result
