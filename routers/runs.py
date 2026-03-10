import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from schemas import (
    RunCreate, RunResponse,
    NodeExecutionCreate, NodeExecutionResponse,
    ValidateExecutionResponse,
    MessageRequest,               # ADDED
    ClarificationSessionResponse  # ADDED
)
from repositories import (
    run_repository, node_execution_repository, project_repository,
    workflow_repository, artifact_repository, session_repository,
    execution_queue_repository    # ADDED
)
from repositories.base import transaction
from use_cases.execute_node import ExecuteNodeUseCase
from dependencies import (
    get_execute_use_case,
    get_llm_stream_service,
    get_prompt_service,
    get_session_service
)
from services.llm_stream_service import LLMStreamService
from prompt_service import PromptService
from session_service import SessionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])

@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(run_data: RunCreate):
    """Создаёт новый Run с проверкой существования проекта и воркфлоу."""
    project = await project_repository.get_project(run_data.project_id)
    if not project:
        raise HTTPException(status_code=400, detail="Project not found")
    workflow = await workflow_repository.get_workflow(run_data.workflow_id)
    if not workflow:
        raise HTTPException(status_code=400, detail="Workflow not found")

    async with transaction() as tx:
        run_id = await run_repository.create_run(
            project_id=run_data.project_id,
            workflow_id=run_data.workflow_id,
            created_by=None,
            tx=tx,
        )
        run = await run_repository.get_run(run_id, tx=tx)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to create run")
    return run

@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    run = await run_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.post("/runs/{run_id}/nodes/{node_id}/execute", response_model=NodeExecutionResponse)
async def execute_node(
    run_id: str,
    node_id: str,
    body: NodeExecutionCreate,
    background_tasks: BackgroundTasks,
    use_case: ExecuteNodeUseCase = Depends(get_execute_use_case),
):
    try:
        execution = await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
            parent_execution_id=body.parent_execution_id,
            idempotency_key=body.idempotency_key,
            input_artifact_ids=body.input_artifact_ids,
            model=None,
            background_tasks=background_tasks,
        )
        return execution
    except ValueError as e:
        logger.error(f"Execute node failed: {e}", exc_info=True)  # добавьте эту строку
        raise HTTPException(status_code=400, detail=str(e))

# ==================== DIALOGUE ENDPOINTS ====================

@router.get("/executions/{exec_id}/messages", response_model=list[dict])
async def get_execution_messages(exec_id: str):
    """
    Возвращает историю сообщений для выполнения, если у него есть clarification-сессия.
    """
    execution = await node_execution_repository.get_node_execution(exec_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    session_id = execution.get("clarification_session_id")
    if not session_id:
        return []  # Нет сессии – пустая история

    session = await session_repository.get_clarification_session(session_id)
    if not session:
        return []  # Сессия аномально отсутствует

    return session.get("history", [])


@router.post("/executions/{exec_id}/messages")
async def send_execution_message(
    exec_id: str,
    req: MessageRequest,
    stream_service: LLMStreamService = Depends(get_llm_stream_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Отправляет сообщение пользователя в диалог выполнения.
    Возвращает потоковый ответ ассистента (text/event-stream).
    """
    # 1. Получаем выполнение и проверяем статус
    execution = await node_execution_repository.get_node_execution(exec_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail="Execution is not in DRAFT status")

    session_id = execution.get("clarification_session_id")
    if not session_id:
        raise HTTPException(status_code=404, detail="No clarification session associated with this execution")

    # 2. Получаем узел и системный промпт
    node = await workflow_repository.get_workflow_node_by_id(execution["node_definition_id"])
    if not node:
        raise HTTPException(status_code=404, detail="Node definition not found")
    system_prompt = node.get("config", {}).get("system_prompt", "You are a helpful assistant.")

    # 3. Сохраняем сообщение пользователя в сессию
    await session_service.add_message_to_session(session_id, "user", req.message)

    # 4. Получаем полную историю сессии для передачи в LLM
    session = await session_service.get_clarification_session(session_id)
    history = session["history"]  # список сообщений с ключами role, content

    # 5. Формируем сообщения для LLM: системный + вся история
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # 6. Определяем модель: можно из запроса или из конфига узла
    model = req.model or node.get("config", {}).get("default_model", "llama-3.3-70b-versatile")

    # 7. Стримим ответ с помощью нового метода stream_chat
    async def generate():
        full_response = ""
        try:
            async for chunk in stream_service.stream_chat(
                messages=messages,
                model_id=model,
                project_id=execution.get("project_id")
            ):
                full_response += chunk
                yield chunk
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"🔴 **STREAMING_ERROR**: {str(e)}"
        finally:
            # После завершения стрима сохраняем полный ответ ассистента
            if full_response:
                await session_service.add_message_to_session(session_id, "assistant", full_response)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/executions/{exec_id}/validate", response_model=ValidateExecutionResponse)
async def validate_execution(
    exec_id: str,
    prompt_service: PromptService = Depends(get_prompt_service),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Валидирует выполнение: создаёт артефакт из последнего сообщения ассистента (если статус DRAFT),
    переводит выполнение в VALIDATED и автоматически создаёт следующий узел (если есть).
    """
    async with transaction() as tx:
        # 1. Блокируем целевую запись выполнения
        target_row = await tx.conn.fetchrow(
            "SELECT * FROM node_executions WHERE id = $1 FOR UPDATE", exec_id
        )
        if not target_row:
            raise HTTPException(status_code=404, detail="Execution not found")
        target = dict(target_row)
        for k in ['id', 'run_id', 'node_definition_id', 'parent_execution_id', 'output_artifact_id']:
            if target.get(k):
                target[k] = str(target[k])

        # 2. Проверяем статус: допускаем DRAFT или COMPLETED
        if target["status"] not in ("DRAFT", "COMPLETED"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot validate execution with status {target['status']}"
            )

        # 3. Если статус DRAFT, создаём артефакт из последнего сообщения ассистента
        artifact_id = target.get("output_artifact_id")
        if target["status"] == "DRAFT":
            session_id = target.get("clarification_session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="DRAFT execution has no clarification session")
            session = await session_service.get_clarification_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Clarification session not found")
            history = session.get("history", [])
            if not history or history[-1]["role"] != "assistant":
                raise HTTPException(status_code=400, detail="No assistant message found to validate")

            last_assistant_msg = history[-1]["content"]
            node = await workflow_repository.get_workflow_node_by_id(target["node_definition_id"], tx=tx)
            if not node:
                raise HTTPException(status_code=404, detail="Node definition not found")

            # Создаём артефакт
            logical_key = f"node-{node['node_id']}-{exec_id}"
            artifact_id = await artifact_repository.save_artifact(
                project_id=target["project_id"],
                artifact_type=node["node_id"],
                content=last_assistant_msg,
                logical_key=logical_key,
                tx=tx
            )
            # Обновляем выполнение: статус COMPLETED + output_artifact_id
            await node_execution_repository.update_node_execution_status(
                exec_id, "COMPLETED", output_artifact_id=artifact_id, tx=tx
            )
            target["status"] = "COMPLETED"
            target["output_artifact_id"] = artifact_id

        # 4. Далее стандартная валидация (как в исходном коде)
        # Блокируем соответствующий run и проверяем его статус
        run_row = await tx.conn.fetchrow(
            "SELECT * FROM runs WHERE id = $1 FOR UPDATE", target["run_id"]
        )
        if not run_row:
            raise HTTPException(status_code=404, detail="Run not found")
        run = dict(run_row)
        if run["status"] != "OPEN":
            raise HTTPException(status_code=409, detail="Run is not OPEN, cannot validate")

        # Ищем активное выполнение для этого node_definition_id и блокируем его
        active_row = await tx.conn.fetchrow("""
            SELECT * FROM node_executions
            WHERE project_id = $1
              AND node_definition_id = $2
              AND status = 'VALIDATED'
              AND superseded_by_id IS NULL
            FOR UPDATE
        """, run["project_id"], target["node_definition_id"])

        superseded_id = None
        previous_active_id = None

        if active_row:
            active = dict(active_row)
            for k in ['id', 'output_artifact_id']:
                if active.get(k):
                    active[k] = str(active[k])
            previous_active_id = active["id"]

            await node_execution_repository.supersede_execution(active["id"], exec_id, tx=tx)
            superseded_id = active["id"]

            if active.get("output_artifact_id"):
                await artifact_repository.update_artifact_status(
                    active["output_artifact_id"], "SUPERSEDED", tx=tx
                )

        # Валидируем текущее выполнение
        await node_execution_repository.validate_execution(exec_id, tx=tx)

        if target.get("output_artifact_id"):
            await artifact_repository.update_artifact_status(
                target["output_artifact_id"], "ACTIVE", tx=tx
            )

        # Обновляем снапшот истины (ADR-006)
        project_id = run["project_id"]
        node_def_id = target["node_definition_id"]
        artifact_id = target.get("output_artifact_id")
        if artifact_id:
            artifact = await artifact_repository.get_artifact(artifact_id, tx=tx)
            logical_key = artifact.get("logical_key") if artifact else None
            version = artifact.get("version") if artifact else None
        else:
            logical_key = None
            version = None

        await tx.conn.execute("""
            INSERT INTO project_truth_snapshot
                (project_id, node_definition_id, execution_id, artifact_id, validated_at,
                 artifact_logical_key, artifact_version)
            VALUES ($1, $2, $3, $4, NOW(), $5, $6)
            ON CONFLICT (project_id, node_definition_id) DO UPDATE
            SET execution_id = EXCLUDED.execution_id,
                artifact_id = EXCLUDED.artifact_id,
                validated_at = EXCLUDED.validated_at,
                artifact_logical_key = EXCLUDED.artifact_logical_key,
                artifact_version = EXCLUDED.artifact_version,
                updated_at = NOW()
        """, project_id, node_def_id, exec_id, artifact_id, logical_key, version)

        # ===== СОЗДАНИЕ СЛЕДУЮЩЕГО УЗЛА =====
        next_execution_id = None
        next_node_id = await node_execution_repository.get_next_node_for_execution(exec_id, tx=tx)
        if next_node_id:
            next_node = await workflow_repository.get_workflow_node_by_id(next_node_id, tx=tx)
            if next_node:
                auto_key = f"auto-{target['run_id']}-{next_node_id}-{uuid.uuid4()}"
                new_exec_id = await node_execution_repository.create_node_execution(
                    run_id=target["run_id"],
                    node_definition_id=next_node_id,
                    parent_execution_id=exec_id,
                    idempotency_key=auto_key,
                    input_artifact_ids=[artifact_id] if artifact_id else [],
                    attempt=1,
                    max_attempts=next_node.get('config', {}).get('max_attempts', 3),
                    retry_parent_id=None,
                    clarification_session_id=None,
                    tx=tx
                )
                if next_node.get('requires_dialogue', False):
                    # Создаём clarification сессию и первое сообщение
                    session_id = await session_repository.create_clarification_session(
                        project_id=run["project_id"],
                        target_artifact_type=next_node['node_id'],
                        tx=tx
                    )
                    await tx.conn.execute("""
                        UPDATE node_executions
                        SET clarification_session_id = $1, status = 'DRAFT', updated_at = NOW()
                        WHERE id = $2
                    """, session_id, new_exec_id)

                    sys_prompt = next_node.get('config', {}).get('system_prompt', 'Начни диалог с пользователем для уточнения требований.')
                    messages = [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": "Начни диалог."}
                    ]
                    model = next_node.get('config', {}).get('default_model', "llama-3.3-70b-versatile")
                    assistant_message = await prompt_service.get_chat_completion(messages, model)
                    await session_repository.add_message_to_session(session_id, "assistant", assistant_message, tx=tx)
                else:
                    await execution_queue_repository.enqueue(new_exec_id, tx=tx)
                next_execution_id = new_exec_id

        updated = await node_execution_repository.get_node_execution(exec_id, tx=tx)

    return ValidateExecutionResponse(
        id=updated["id"],
        status=updated["status"],
        superseded_id=superseded_id,
        previous_active_id=previous_active_id,
        next_execution_id=next_execution_id,
    )


# ==================== EXISTING ENDPOINTS (unchanged) ====================

@router.post("/runs/{run_id}/freeze", response_model=RunResponse)
async def freeze_run(run_id: str):
    async with transaction() as tx:
        updated = await run_repository.update_run_status(
            run_id, "FROZEN", expected_status="OPEN", tx=tx
        )
        if not updated:
            run = await run_repository.get_run(run_id, tx=tx)
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            raise HTTPException(
                status_code=409,
                detail=f"Cannot freeze run with status {run['status']} (expected OPEN)"
            )
        run = await run_repository.get_run(run_id, tx=tx)
    return run

@router.post("/runs/{run_id}/archive", response_model=RunResponse)
async def archive_run(run_id: str):
    async with transaction() as tx:
        updated = await run_repository.update_run_status(
            run_id, "ARCHIVED", expected_status="FROZEN", tx=tx
        )
        if not updated:
            run = await run_repository.get_run(run_id, tx=tx)
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            raise HTTPException(
                status_code=409,
                detail=f"Cannot archive run with status {run['status']} (expected FROZEN)"
            )
        run = await run_repository.get_run(run_id, tx=tx)
    return run

@router.post("/executions/{exec_id}/supersede")
async def supersede_execution(exec_id: str, new_execution_id: str):
    async with transaction() as tx:
        exec_record = await node_execution_repository.get_node_execution(exec_id, tx=tx)
        if not exec_record:
            raise HTTPException(status_code=404, detail="Execution not found")
        if exec_record["status"] not in ("VALIDATED", "COMPLETED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot supersede execution with status {exec_record['status']}"
            )

        run_row = await tx.conn.fetchrow(
            "SELECT * FROM runs WHERE id = $1 FOR UPDATE", exec_record["run_id"]
        )
        if not run_row or run_row["status"] != "OPEN":
            raise HTTPException(status_code=409, detail="Run is not OPEN, cannot supersede")

        new_exec = await node_execution_repository.get_node_execution(new_execution_id, tx=tx)
        if not new_exec:
            raise HTTPException(status_code=404, detail="New execution not found")

        await node_execution_repository.supersede_execution(exec_id, new_execution_id, tx=tx)

    return {"status": "superseded"}