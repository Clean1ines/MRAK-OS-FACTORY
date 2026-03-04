import logging
from typing import Optional, List
from fastapi import BackgroundTasks  # если нужны фоновые задачи, но пока не используем
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
            # Для этого нужно получить workflow_id по node_id (узел привязан к workflow)
            node = await workflow_repository.get_workflow_node_by_id(req.node_id)
            if not node:
                raise ValueError(f"Node {req.node_id} not found")
            workflow_id = node["workflow_id"]
            # Ищем открытый run для этого workflow (последний созданный)
            runs = await run_repository.list_runs(project_id=node.get("project_id"))  # предполагаем, что у node есть project_id
            open_runs = [r for r in runs if r["status"] == "OPEN"]
            if open_runs:
                run = open_runs[0]  # берём первый (самый новый)
            else:
                # Создаём новый Run
                project_id = node.get("project_id")  # должно быть в node
                run_id = await run_repository.create_run(project_id, workflow_id, created_by="system")
                run = await run_repository.get_run(run_id)
            req.run_id = run["id"]

        # 2. Генерируем idempotency_key, если не передан
        idempotency_key = req.idempotency_key
        if not idempotency_key:
            # Генерируем на основе параметров (например, хэш от node_id + input_artifact_ids)
            # Для простоты используем UUID
            idempotency_key = str(uuid4())

        # 3. Проверяем существующее выполнение по уникальным полям
        existing = await node_execution_repository.find_existing_execution(
            run_id=req.run_id,
            node_definition_id=req.node_id,
            parent_execution_id=req.parent_execution_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            # Если уже есть (даже FAILED), возвращаем его вместе с артефактом (если есть)
            # Загружаем артефакт, если он есть
            artifact = None
            if existing["output_artifact_id"]:
                artifact = await artifact_repository.get_artifact(existing["output_artifact_id"])
            return {
                "execution": existing,
                "artifact": artifact,
                "existing": True,
            }

        # 4. Создаём новое выполнение (PROCESSING)
        async with transaction() as tx:
            exec_id = await node_execution_repository.create_node_execution(
                run_id=req.run_id,
                node_definition_id=req.node_id,
                parent_execution_id=req.parent_execution_id,
                idempotency_key=idempotency_key,
                input_artifact_ids=req.input_artifact_ids,
                tx=tx,
            )
            # Получаем только что созданную запись для ответа (без артефакта пока)
            new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)

        # 5. Генерация артефакта
        try:
            # Получаем узел для конфигурации генерации
            node = await workflow_repository.get_workflow_node_by_id(req.node_id)
            if not node:
                raise RuntimeError(f"Node {req.node_id} not found (concurrent deletion?)")

            # Формируем generation_config из node.config
            node_config = node.get('config', {})
            generation_config = {
                'system_prompt': node_config.get('system_prompt'),
                'user_prompt_template': node_config.get('user_prompt_template'),
                'required_input_types': node_config.get('required_input_types', [])
            }

            # Загружаем входные артефакты
            input_artifacts = await artifact_repository.get_artifacts_by_ids(req.input_artifact_ids)

            # Вызываем генерацию
            artifact_id = await self.artifact_service.generate_artifact(
                artifact_type=node.get('node_id'),  # или другое поле, определяющее тип
                input_artifacts=input_artifacts,
                user_input=req.feedback,
                model_id=req.model,
                project_id=run["project_id"],
                generation_config=generation_config,
            )

            # 6. Обновляем выполнение: статус COMPLETED, привязываем артефакт
            async with transaction() as tx:
                await node_execution_repository.update_node_execution_status(
                    exec_id=exec_id,
                    status="COMPLETED",
                    output_artifact_id=artifact_id,
                    tx=tx,
                )
                # Также обновляем артефакт: добавляем node_execution_id
                await artifact_repository.update_artifact_node_execution(artifact_id, exec_id, tx=tx)

            # Получаем финальное выполнение и артефакт
            updated_exec = await node_execution_repository.get_node_execution(exec_id)
            artifact = await artifact_repository.get_artifact(artifact_id)

        except Exception as e:
            # Ошибка генерации – помечаем выполнение как FAILED
            logger.error(f"Execution {exec_id} failed: {e}", exc_info=True)
            async with transaction() as tx:
                await node_execution_repository.update_node_execution_status(
                    exec_id=exec_id,
                    status="FAILED",
                    tx=tx,
                )
            # Пробрасываем исключение или возвращаем ошибку
            raise

        return {
            "execution": updated_exec,
            "artifact": artifact,
            "existing": False,
        }
