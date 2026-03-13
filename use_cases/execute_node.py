# use_cases/execute_node.py
import logging
from typing import Optional, List
from fastapi import BackgroundTasks

from repositories import (
    run_repository,
    workflow_repository,
    node_execution_repository,
    execution_queue_repository,
    session_repository,
)
from repositories.base import transaction
from prompt_service import PromptService
from session_service import SessionService

logger = logging.getLogger(__name__)

class ExecuteNodeUseCase:
    """
    Use case для идемпотентного выполнения узла в рамках Run.
    Создаёт запись выполнения и, если узел требует диалога,
    инициализирует clarification-сессию; иначе помещает задачу в очередь.
    """

    def __init__(self, artifact_service, prompt_service: Optional[PromptService] = None, session_service: Optional[SessionService] = None):
        self.artifact_service = artifact_service
        self.prompt_service = prompt_service
        self.session_service = session_service

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

            # 4. Ищем последнюю попытку по base_key
            last = await node_execution_repository.find_last_attempt_by_base_key(
                run_id=run_id,
                node_definition_id=node_definition_id,
                parent_execution_id=parent_execution_id,
                base_idempotency_key=idempotency_key,
                tx=tx
            )

            if last:
                if last["status"] in ("COMPLETED", "PROCESSING"):
                    return last

                if last["status"] == "FAILED" and last["attempt"] < last["max_attempts"]:
                    exec_id = await node_execution_repository.create_retry_attempt(last, tx=tx)
                    new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)
                    if not new_exec:
                        raise RuntimeError("Failed to retrieve newly created execution")
                else:
                    return last
            else:
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

            requires_dialogue = node.get('requires_dialogue', False)

            if requires_dialogue:
                if not self.prompt_service or not self.session_service:
                    raise RuntimeError("PromptService and SessionService are required for dialogue nodes")

                # Получаем системный промпт из конфига узла (приоритет custom_prompt, затем system_prompt)
                system_prompt = node.get('config', {}).get('custom_prompt') or node.get('config', {}).get('system_prompt', '')

                # Создаём clarification сессию
                session_id = await session_repository.create_clarification_session(
                    project_id=run['project_id'],
                    target_artifact_type=node['node_id'],
                    tx=tx
                )

                # Сохраняем системный промпт в context_summary сессии (как простую строку)
                await tx.conn.execute("""
                    UPDATE clarification_sessions
                    SET context_summary = $1
                    WHERE id = $2
                """, system_prompt, session_id)

                # Обновляем выполнение: привязываем сессию и ставим статус DRAFT
                await tx.conn.execute("""
                    UPDATE node_executions
                    SET clarification_session_id = $1, status = 'DRAFT', updated_at = NOW()
                    WHERE id = $2
                """, session_id, exec_id)

                new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)
                # Не ставим в очередь
            else:
                await execution_queue_repository.enqueue(exec_id, tx=tx)

            return new_exec