import logging
from typing import Optional, List
from fastapi import BackgroundTasks
from uuid import UUID, uuid4

from repositories import (
    run_repository,
    workflow_repository,
    node_execution_repository,
    artifact_repository,
)
from repositories.base import transaction
from artifact_service import ArtifactService
from schemas import ExecuteStepRequest
from validation import ValidationError

logger = logging.getLogger(__name__)

class ExecuteWorkflowStepUseCase:
    """Use case для выполнения шага воркфлоу с интеграцией NodeExecution."""

    def __init__(self, artifact_service: ArtifactService):
        self.artifact_service = artifact_service

    async def execute(self, req: ExecuteStepRequest) -> dict:
        # 1. Определяем или создаём Run, если не передан
        if req.run_id:
            run = await run_repository.get_run(req.run_id)
            if not run:
                raise ValueError(f"Run {req.run_id} not found")
            if run["status"] != "OPEN":
                raise ValueError(f"Run {run['status']} is not OPEN")
        else:
            # Обратная совместимость: находим или создаём Run автоматически
            node = await workflow_repository.get_workflow_node_by_id(req.node_id)
            if not node:
                raise ValueError(f"Node {req.node_id} not found")
            workflow_id = node["workflow_id"]
            runs = await run_repository.list_runs(project_id=node.get("project_id"))
            open_runs = [r for r in runs if r["status"] == "OPEN"]
            if open_runs:
                run = open_runs[0]
            else:
                project_id = node.get("project_id")
                if not project_id:
                    raise ValueError("Node has no project_id")
                run_id = await run_repository.create_run(project_id, workflow_id, created_by="system")
                run = await run_repository.get_run(run_id)
            req.run_id = run["id"]

        # 2. Проверяем узел (он может потребоваться и для генерации, и для поиска)
        node = await workflow_repository.get_workflow_node_by_id(req.node_id)
        if not node:
            raise ValueError(f"Node {req.node_id} not found")
        if str(node["workflow_id"]) != str(run["workflow_id"]):
            raise ValueError(f"Node does not belong to workflow {run['workflow_id']}")

        # 3. Проверяем родителя, если он указан
        if req.parent_execution_id:
            parent = await node_execution_repository.get_node_execution(req.parent_execution_id)
            if not parent:
                raise ValueError(f"Parent execution {req.parent_execution_id} not found")
            if parent["status"] not in ("COMPLETED", "VALIDATED"):
                raise ValueError(f"Parent execution status must be COMPLETED or VALIDATED, got {parent['status']}")

        # 4. Генерируем idempotency_key, если не передан
        idempotency_key = req.idempotency_key
        if not idempotency_key:
            idempotency_key = str(uuid4())

        # 5. Проверяем существующее выполнение по уникальным полям
        existing = await node_execution_repository.find_existing_execution(
            run_id=req.run_id,
            node_definition_id=req.node_id,
            parent_execution_id=req.parent_execution_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            artifact = None
            if existing["output_artifact_id"]:
                artifact = await artifact_repository.get_artifact(existing["output_artifact_id"])
            return {
                "execution": existing,
                "artifact": artifact,
                "existing": True,
            }

        # 6. Создаём новое выполнение (PROCESSING)
        async with transaction() as tx:
            exec_id = await node_execution_repository.create_node_execution(
                run_id=req.run_id,
                node_definition_id=req.node_id,
                parent_execution_id=req.parent_execution_id,
                idempotency_key=idempotency_key,
                input_artifact_ids=req.input_artifact_ids,
                tx=tx,
            )
            new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)

        # 7. Генерация артефакта
        try:
            node_config = node.get('config', {})
            generation_config = {
                'system_prompt': node_config.get('system_prompt'),
                'user_prompt_template': node_config.get('user_prompt_template'),
                'required_input_types': node_config.get('required_input_types', [])
            }
            input_artifacts = await artifact_repository.get_artifacts_by_ids(req.input_artifact_ids)
            artifact_id = await self.artifact_service.generate_artifact(
                artifact_type=node.get('node_id'),
                input_artifacts=input_artifacts,
                user_input=req.feedback,
                model_id=req.model,
                project_id=run["project_id"],
                generation_config=generation_config,
            )

            async with transaction() as tx:
                await node_execution_repository.update_node_execution_status(
                    exec_id=exec_id,
                    status="COMPLETED",
                    output_artifact_id=artifact_id,
                    tx=tx,
                )
                await artifact_repository.update_artifact_node_execution(artifact_id, exec_id, tx=tx)

            updated_exec = await node_execution_repository.get_node_execution(exec_id)
            artifact = await artifact_repository.get_artifact(artifact_id)

        except Exception as e:
            logger.error(f"Execution {exec_id} failed: {e}", exc_info=True)
            async with transaction() as tx:
                await node_execution_repository.update_node_execution_status(
                    exec_id=exec_id,
                    status="FAILED",
                    tx=tx,
                )
            raise

        return {
            "execution": updated_exec,
            "artifact": artifact,
            "existing": False,
        }
