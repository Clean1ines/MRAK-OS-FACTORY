import logging
from typing import Optional, List
from fastapi import BackgroundTasks

from repositories import (
    run_repository,
    workflow_repository,
    node_execution_repository,
    execution_queue_repository,
)
from repositories.base import transaction

logger = logging.getLogger(__name__)

class ExecuteNodeUseCase:
    """
    Use case для идемпотентного выполнения узла в рамках Run.
    Создаёт запись выполнения и помещает задачу в очередь.
    """

    def __init__(self, artifact_service):
        # artifact_service не используется напрямую, но сохраняется для совместимости
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
        """
        Выполняет логику создания выполнения узла с учётом идемпотентности
        и повторных попыток. Задача ставится в очередь execution_queue.
        """
        async with transaction() as tx:
            # 1. Блокируем run и проверяем статус
            run_row = await tx.conn.fetchrow(
                "SELECT * FROM runs WHERE id = $1 FOR UPDATE", run_id
            )
            if not run_row:
                raise ValueError(f"Run {run_id} not found")
            run = dict(run_row)
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
                parent = await node_execution_repository.get_node_execution(parent_execution_id, tx=tx)
                if not parent:
                    raise ValueError(f"Parent execution {parent_execution_id} not found")
                if parent["status"] not in ("COMPLETED", "VALIDATED"):
                    raise ValueError(f"Parent status must be COMPLETED or VALIDATED, got {parent['status']}")

            # 4. Ищем последнюю попытку по base_key (idempotency_key теперь трактуется как base_key)
            last = await node_execution_repository.find_last_attempt_by_base_key(
                run_id=run_id,
                node_definition_id=node_definition_id,
                parent_execution_id=parent_execution_id,
                base_idempotency_key=idempotency_key,
                tx=tx
            )

            if last:
                # Существующее выполнение найдено
                if last["status"] in ("COMPLETED", "PROCESSING"):
                    # Возвращаем текущее (уже завершённое или выполняющееся)
                    return last

                if last["status"] == "FAILED" and last["attempt"] < last["max_attempts"]:
                    # Создаём повторную попытку
                    new_exec_id = await node_execution_repository.create_retry_attempt(last, tx=tx)
                    new_exec = await node_execution_repository.get_node_execution(new_exec_id, tx=tx)
                    if not new_exec:
                        raise RuntimeError("Failed to retrieve newly created execution")
                    # Ставим в очередь
                    await execution_queue_repository.enqueue(new_exec_id, tx=tx)
                    return new_exec

                # Возвращаем последнее FAILED (попытки исчерпаны)
                return last
            else:
                # Первая попытка
                max_attempts = node.get('config', {}).get('max_attempts', 3)
                exec_id = await node_execution_repository.create_node_execution(
                    run_id=run_id,
                    node_definition_id=node_definition_id,
                    parent_execution_id=parent_execution_id,
                    idempotency_key=idempotency_key,
                    input_artifact_ids=input_artifact_ids,
                    attempt=1,
                    max_attempts=max_attempts,
                    retry_parent_id=None,
                    tx=tx
                )
                new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)
                if not new_exec:
                    raise RuntimeError("Failed to retrieve newly created execution")
                # Ставим в очередь
                await execution_queue_repository.enqueue(exec_id, tx=tx)
                return new_exec