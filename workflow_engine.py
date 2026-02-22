# CHANGED: Refactored get_next_step using WorkflowGraph
import logging
from typing import Optional, Dict, Any, List
from repositories.workflow_repository import (
    list_workflows, get_workflow_nodes, get_workflow_edges
)
from repositories.artifact_repository import (
    get_last_validated_artifact, get_artifact, get_last_version_by_parent_and_type
)
from repositories.base import transaction
from domain.workflow_graph import WorkflowGraph  # ADDED

logger = logging.getLogger("WORKFLOW-ENGINE")

class WorkflowEngine:
    def __init__(self, artifact_service):
        self.artifact_service = artifact_service

    async def get_default_workflow_id(self) -> Optional[str]:
        workflows = await list_workflows()
        for wf in workflows:
            if wf.get('is_default'):
                return wf['id']
        logger.error("No default workflow found in database")
        return None

    async def get_next_step(self, project_id: str) -> Optional[Dict[str, Any]]:
        # Get last validated artifact
        last_valid = await get_last_validated_artifact(project_id)

        # Determine which workflow to use (always default for now)
        workflow_id = await self.get_default_workflow_id()
        if not workflow_id:
            return None

        # Load graph
        nodes = await get_workflow_nodes(workflow_id)
        edges = await get_workflow_edges(workflow_id)
        graph = WorkflowGraph(nodes, edges)

        if not last_valid:
            # No artifacts yet: return start node
            start_nodes = graph.get_start_nodes()
            if not start_nodes:
                logger.error("No start node found in workflow")
                return None
            start_node_id = start_nodes[0]
            start_node = graph.get_node(start_node_id)
            return {
                "next_stage": start_node_id,
                "prompt_type": start_node['prompt_key'],
                "parent_id": None,
                "description": f"Сгенерировать {start_node_id}"
            }

        # There is a last validated artifact: find its node and then next
        current_node = graph.get_node(last_valid['type'])
        if not current_node:
            logger.warning(f"Artifact type {last_valid['type']} not found in default workflow")
            return None

        if graph.is_finished(current_node['node_id']):
            return {
                "next_stage": "finished",
                "prompt_type": None,
                "parent_id": last_valid['id'],
                "description": "Проект завершён"
            }

        next_node_id = graph.get_next_node(current_node['node_id'])
        next_node = graph.get_node(next_node_id)
        if not next_node:
            logger.error(f"Next node {next_node_id} not found in nodes")
            return None

        return {
            "next_stage": next_node_id,
            "prompt_type": next_node['prompt_key'],
            "parent_id": last_valid['id'],
            "description": f"Сгенерировать {next_node_id}"
        }

    async def execute_step(self, project_id: str, step_info: Dict, model: Optional[str] = None) -> Dict[str, Any]:
        prompt_type = step_info['prompt_type']
        parent_id = step_info.get('parent_id')

        async with transaction() as tx:
            if parent_id:
                existing = await get_last_version_by_parent_and_type(parent_id, prompt_type, tx=tx)
                if existing and existing['status'] == 'VALIDATED':
                    return {
                        "artifact_id": existing['id'],
                        "artifact_type": prompt_type,
                        "content": existing['content'],
                        "parent_id": parent_id,
                        "next_stage": step_info['next_stage'],
                        "existing": True
                    }

            parent_artifact = await get_artifact(parent_id, tx=tx) if parent_id else None

        new_id = await self.artifact_service.generate_artifact(
            artifact_type=prompt_type,
            user_input="",
            parent_artifact=parent_artifact,
            model_id=model,
            project_id=project_id
        )

        async with transaction() as tx:
            artifact = await get_artifact(new_id, tx=tx)
        return {
            "artifact_id": new_id,
            "artifact_type": prompt_type,
            "content": artifact['content'] if artifact else None,
            "parent_id": parent_id,
            "next_stage": step_info['next_stage'],
            "existing": False
        }
