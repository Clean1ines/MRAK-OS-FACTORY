import logging
from typing import Optional, List
from fastapi import BackgroundTasks

from repositories import (
    run_repository,
    workflow_repository,
    node_execution_repository,
    execution_queue_repository,
    session_repository,  # ADDED for dialogue support
)
from repositories.base import transaction
# ADDED for dialogue support
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
        """
        :param artifact_service: сохранён для обратной совместимости (не используется)
        :param prompt_service: требуется для узлов с requires_dialogue = true
        :param session_service: требуется для узлов с requires_dialogue = true
        """
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
        """
        Выполняет логику создания выполнения узла с учётом идемпотентности
        и повторных попыток. Для диалоговых узлов создаёт сессию и первое сообщение.
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

            # 2. Проверяем узел (получаем его с новым полем requires_dialogue)
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

            # 5. Определяем, нужно ли создавать новое выполнение
            if last:
                # Существующее выполнение найдено
                if last["status"] in ("COMPLETED", "PROCESSING"):
                    return last

                if last["status"] == "FAILED" and last["attempt"] < last["max_attempts"]:
                    # Создаём повторную попытку
                    exec_id = await node_execution_repository.create_retry_attempt(last, tx=tx)
                    new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)
                    if not new_exec:
                        raise RuntimeError("Failed to retrieve newly created execution")
                else:
                    # Попытки исчерпаны или другой статус
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

            # ===== НОВАЯ ЛОГИКА: обработка диалоговых узлов =====
            requires_dialogue = node.get('requires_dialogue', False)

            if requires_dialogue:
                # Проверяем наличие необходимых сервисов
                if not self.prompt_service or not self.session_service:
                    raise RuntimeError("PromptService and SessionService are required for dialogue nodes")

                # 1. Создаём clarification сессию
                session_id = await session_repository.create_clarification_session(
                    project_id=run['project_id'],
                    target_artifact_type=node['node_id'],  # используем текстовый ID узла как тип
                    tx=tx
                )

                # 2. Обновляем выполнение: устанавливаем сессию и статус DRAFT
                await tx.conn.execute("""
                    UPDATE node_executions
                    SET clarification_session_id = $1, status = 'DRAFT', updated_at = NOW()
                    WHERE id = $2
                """, session_id, exec_id)

                # 3. Генерируем первое сообщение ассистента
                system_prompt = node.get('config', {}).get('system_prompt', '')
                if not system_prompt:
                    # Если системный промпт не задан, используем нейтральный
                    system_prompt = "Начни диалог с пользователем для уточнения требований."

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Начни диалог."}
                ]

                # Используем переданную модель или дефолтную
                effective_model = model or "llama-3.3-70b-versatile"
                assistant_message = await self.prompt_service.get_chat_completion(messages, effective_model)

                # 4. Сохраняем сообщение ассистента в сессию
                await session_repository.add_message_to_session(session_id, "assistant", assistant_message, tx=tx)

                # 5. Получаем обновлённый объект выполнения
                new_exec = await node_execution_repository.get_node_execution(exec_id, tx=tx)

                # Не ставим в очередь
            else:
                # Обычный узел: ставим в очередь
                await execution_queue_repository.enqueue(exec_id, tx=tx)

            return new_exec