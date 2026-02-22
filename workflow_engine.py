# workflow_engine.py
# ADDED: Engine for executing workflows (to be populated later)

class WorkflowEngine:
    def __init__(self, artifact_service, prompt_service, session_service):
        self.artifact_service = artifact_service
        self.prompt_service = prompt_service
        self.session_service = session_service

    async def run_workflow(self, workflow_id, project_id, initial_inputs):
        """Placeholder – will be implemented in later steps."""
        pass
