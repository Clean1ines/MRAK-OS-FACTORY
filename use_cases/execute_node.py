import logging
from typing import Optional, List
from fastapi import BackgroundTasks

from repositories import (
    run_repository,
    workflow_repository,
    node_execution_repository,
    artifact_repository,
)
from artifact_service import ArtifactService
from repositories.base import transaction

logger = logging.getLogger(__name__)

class ExecuteNodeUseCase:
    """Use case для идемпотентного выполнения узла в рамках Run."""

    def __init__(self, artifact_service: ArtifactService):
        self.artifact_service = artifact_service

    async def execute(
        self,
        run_id: str,
        node_definition_id: str,
        parent_execution_id: Optional[str],
        idempotency_key: str,
        input_artifact_ids: Optional[List[str]],
        model: Optional[str],
        background_tasks: BackgroundTasks,
    ):
        # 1. Проверяем run
        run = await run_repository.get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        if run["status"] != "OPEN":
            raise ValueError(f"Run {run_id} is not OPEN (status={run['status']})")

        # 2. Проверяем узел
        node = await workflow_repository.get_workflow_node_by_id(node_definition_id)
        if not node:
            raise ValueError(f"Node {node_definition_id} not found")
        if str(node["workflow_id"]) != str(run["workflow_id"]):
            raise ValueError(f"Node does not belong to workflow {run['workflow_id']}")

        # 3. Проверяем родителя
        if parent_execution_id:
            parent = await node_execution_repository.get_node_execution(parent_execution_id)
            if not parent:
                raise ValueError(f"Parent execution {parent_execution_id} not found")
            if parent["status"] not in ("COMPLETED", "VALIDATED"):
                raise ValueError(f"Parent status must be COMPLETED or VALIDATED, got {parent['status']}")

        # 4. Ищем существующее выполнение по идемпотентному ключу
        existing = await node_execution_repository.find_existing_execution(
            run_id=run_id,
            node_definition_id=node_definition_id,
            parent_execution_id=parent_execution_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            # Возвращаем существующее выполнение независимо от его статуса
            return existing

        # 5. Создаём новое выполнение
        async with transaction() as tx:
            exec_id = await node_execution_repository.create_node_execution(
                run_id=run_id,
                node_definition_id=node_definition_id,
                parent_execution_id=parent_execution_id,
                idempotency_key=idempotency_key,
                input_artifact_ids=input_artifact_ids,
                tx=tx,
            )
            new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)

        # 6. Запускаем фоновую задачу
        background_tasks.add_task(
            self._complete_execution,
            exec_id=exec_id,
            node_definition_id=node_definition_id,
            project_id=run["project_id"],
            model=model,
            input_artifact_ids=input_artifact_ids or [],
        )

        return new_exec

    async def _complete_execution(
        self,
        exec_id: str,
        node_definition_id: str,
        project_id: str,
        model: Optional[str],
        input_artifact_ids: List[str],
    ):
        logger.info(f"Starting background completion for execution {exec_id}")
        try:
            node = await workflow_repository.get_workflow_node_by_id(node_definition_id)
            if not node:
                raise RuntimeError(f"Node {node_definition_id} not found")

            node_config = node.get('config', {})
            generation_config = {
                'system_prompt': node_config.get('system_prompt'),
                'user_prompt_template': node_config.get('user_prompt_template'),
                'required_input_types': node_config.get('required_input_types', [])
            }

            artifact_type = node.get('node_id')
            input_artifacts = await artifact_repository.get_artifacts_by_ids(input_artifact_ids)

            artifact_id = await self.artifact_service.generate_artifact(
                artifact_type=artifact_type,
                input_artifacts=input_artifacts,
                user_input="",
                model_id=model,
                project_id=project_id,
                generation_config=generation_config
            )

            async with transaction() as tx:
                await node_execution_repository.update_node_execution_status(
                    exec_id=exec_id,
                    status="COMPLETED",
                    output_artifact_id=artifact_id,
                    tx=tx,
                )
            logger.info(f"Execution {exec_id} completed with artifact {artifact_id}")

        except Exception as e:
            logger.error(f"Background execution {exec_id} failed: {e}", exc_info=True)
            async with transaction() as tx:
                await node_execution_repository.update_node_execution_status(
                    exec_id=exec_id,
                    status="FAILED",
                    tx=tx,
                )
